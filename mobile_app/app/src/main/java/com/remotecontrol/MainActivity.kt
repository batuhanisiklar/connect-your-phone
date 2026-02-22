package com.remotecontrol

import android.Manifest
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.media.projection.MediaProjectionManager
import android.net.wifi.WifiManager
import android.content.SharedPreferences
import android.os.Build
import android.os.Bundle
import android.text.format.Formatter
import android.util.Log
import android.widget.*
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import kotlinx.coroutines.*

/**
 * Ana Aktivite
 * ============
 * - 6 haneli bağlantı kodunu gösterir
 * - Signaling sunucusuna bağlanır
 * - PC eşleşince MediaProjection izni ister ve ekran yayınını başlatır
 * - Kamera aç/kapat komutlarını işler
 * - Erişilebilirlik servisi yönlendirmesi ve touch/swipe komutları
 *
 * Kullanıcı bir kez çalıştırır, kod gösterilir ve bağlantıyı bekler.
 */
class MainActivity : AppCompatActivity() {

    companion object {
        private const val TAG = "MainActivity"
        private const val PREFS_NAME = "RemoteControlPrefs"
        private const val KEY_SERVER_IP = "server_ip"
        private const val DEFAULT_SERVER_IP = "192.168.1.103"  // Aynı ağdaki PC'nin IP'si
        private const val SIGNALING_URL = "wss://connect-your-phone.onrender.com"
        // Emülatörde host makineye ulaşmak için 10.0.2.2 kullanılır
        // Gerçek cihazda 192.168.1.103:8765 (signaling sunucusunun IP'si)

        private val IS_EMULATOR = (android.os.Build.FINGERPRINT.startsWith("generic")
                || android.os.Build.FINGERPRINT.startsWith("unknown")
                || android.os.Build.MODEL.contains("Emulator")
                || android.os.Build.MODEL.contains("Android SDK built for x86")
                || android.os.Build.MANUFACTURER.contains("Genymotion")
                || android.os.Build.BRAND.startsWith("generic"))
    }

    // UI
    private lateinit var tvCode: TextView
    private lateinit var tvStatus: TextView
    private lateinit var tvIpPort: TextView
    private lateinit var etServerIp: EditText
    private lateinit var btnConnect: Button
    private lateinit var btnStopStream: Button
    private lateinit var tvAccessibility: TextView

    // Network
    private var signalingClient: SignalingClient? = null
    private val scope = CoroutineScope(Dispatchers.Main + SupervisorJob())

    // MediaProjection izni
    private var pendingMediaProjectionResult: (() -> Unit)? = null
    private val mediaProjectionLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        if (result.resultCode == Activity.RESULT_OK && result.data != null) {
            startScreenStream(result.resultCode, result.data!!)
        } else {
            updateStatus("⚠ Ekran kaydı izni reddedildi")
        }
    }

    // Kamera izni
    private val cameraPermLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        if (granted) {
            startCameraStream(useFront = false)
        } else {
            updateStatus("⚠ Kamera izni reddedildi")
        }
    }

    // Bildirim izni (Android 13+)
    private val notifPermLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { /* İzin verilmese de devam et */ }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        initViews()
        requestNotificationPermission()
        checkAccessibilityService()
        autoConnect()
    }

    private fun initViews() {
        tvCode = findViewById(R.id.tv_code)
        tvStatus = findViewById(R.id.tv_status)
        tvIpPort = findViewById(R.id.tv_ip_port)
        etServerIp = findViewById(R.id.et_server_ip)
        btnConnect = findViewById(R.id.btn_connect)
        btnStopStream = findViewById(R.id.btn_stop_stream)
        tvAccessibility = findViewById(R.id.tv_accessibility)

        btnConnect.setOnClickListener { autoConnect() }
        btnStopStream.setOnClickListener { stopAllStreams() }
        tvAccessibility.setOnClickListener {
            startActivity(Intent(android.provider.Settings.ACTION_ACCESSIBILITY_SETTINGS))
        }
        btnStopStream.isEnabled = false
    }

    private fun getSignalingUrl(): String {
        return SIGNALING_URL
    }

    private fun autoConnect() {
        val serverUrl = SIGNALING_URL
        
        updateStatus("🔄 Signaling sunucusuna bağlanıyor...")
        btnConnect.isEnabled = false

        signalingClient?.disconnect()
        signalingClient = SignalingClient(
            serverUrl = serverUrl,
            onPaired = { _ ->
                runOnUiThread {
                    updateStatus("✅ PC bağlandı!")
                    btnStopStream.isEnabled = true
                    if (IS_EMULATOR) {
                        // Emülatörde MediaProjection çalışmaz → kamera stream kullan
                        updateStatus("✅ PC bağlandı! Kamera yayını başlıyor (emülatör)...")
                        requestCameraAccess(useFront = false)
                    } else {
                        // Gerçek cihazda ekran yakalama
                        updateStatus("✅ PC bağlandı! Ekran yayını başlıyor...")
                        requestScreenCapture()
                    }
                }
            },
            onCommand = { action, params ->
                handleCommand(action, params)
            },
            onDisconnected = {
                runOnUiThread {
                    updateStatus("🔴 Bağlantı kesildi — Yeniden bağlanmak için butona basın")
                    btnConnect.isEnabled = true
                    btnStopStream.isEnabled = false
                    // tvCode — kodu silmiyoruz, kullanıcı tekrar deneyebilir
                }
            }
        )
        signalingClient?.connect()

        // Kodu göster
        val code = signalingClient!!.sessionCode
        tvCode.text = code
        updateStatus("⏳ PC bağlantısı bekleniyor...")
        Log.i(TAG, "Session code: $code")
    }

    private fun handleCommand(action: String, params: Map<String, Any>) {
        Log.d(TAG, "Command: $action $params")
        when (action) {
            "touch" -> {
                val x = (params["x"] as? Double)?.toFloat() ?: return
                val y = (params["y"] as? Double)?.toFloat() ?: return
                ControlReceiver.instance?.performTouch(x, y)
            }
            "swipe" -> {
                val x1 = (params["x1"] as? Double)?.toFloat() ?: return
                val y1 = (params["y1"] as? Double)?.toFloat() ?: return
                val x2 = (params["x2"] as? Double)?.toFloat() ?: return
                val y2 = (params["y2"] as? Double)?.toFloat() ?: return
                ControlReceiver.instance?.performSwipe(x1, y1, x2, y2)
            }
            "key_event" -> {
                val keyCode = (params["key_code"] as? Int) ?: return
                ControlReceiver.instance?.performKeyEvent(keyCode)
            }
            "camera_on" -> {
                runOnUiThread { requestCameraAccess(useFront = false) }
            }
            "camera_off" -> {
                runOnUiThread { stopCameraStream() }
            }
            else -> Log.w(TAG, "Unknown command: $action")
        }
    }

    private fun requestScreenCapture() {
        val pm = getSystemService(MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
        mediaProjectionLauncher.launch(pm.createScreenCaptureIntent())
    }

    private fun startScreenStream(resultCode: Int, data: Intent) {
        val intent = Intent(this, ScreenStreamService::class.java).apply {
            putExtra(ScreenStreamService.EXTRA_RESULT_CODE, resultCode)
            putExtra(ScreenStreamService.EXTRA_RESULT_DATA, data)
        }
        startForegroundService(intent)

        // Servis başladıktan sonra stream URL'sini PC'ye bildir
        val ip = getDeviceIp()
        
        // Geçersiz IP'ler için HTTP stream URL'si gönderme
        // PC sadece WebSocket frame'lerini kullanacak
        if (ip != "0.0.0.0" && !ip.startsWith("10.0.2.")) {
            val streamUrl = "http://$ip:${ScreenStreamService.PORT}/stream"
            signalingClient?.notifyStreamReady(streamUrl)
            tvIpPort.text = "Stream: $streamUrl"
        } else {
            // Emülatör veya geçersiz IP - sadece WebSocket kullan
            signalingClient?.notifyStreamReady("")  // Boş URL = sadece WebSocket
            tvIpPort.text = "Ekran WebSocket üzerinden gönderiliyor"
        }
        updateStatus("🟢 Ekran yayını aktif")
    }

    private fun requestCameraAccess(useFront: Boolean) {
        when {
            ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA)
                    == PackageManager.PERMISSION_GRANTED -> startCameraStream(useFront)
            else -> cameraPermLauncher.launch(Manifest.permission.CAMERA)
        }
    }

    private fun startCameraStream(useFront: Boolean) {
        val intent = Intent(this, CameraStreamService::class.java).apply {
            putExtra(CameraStreamService.EXTRA_USE_FRONT, useFront)
        }
        startForegroundService(intent)

        // Kamera zaten WebSocket üzerinden frame gönderiyor
        // HTTP stream URL'si sadece geçerli IP'ler için gönder
        val ip = getDeviceIp()
        if (ip != "0.0.0.0" && !ip.startsWith("10.0.2.")) {
            val streamUrl = "http://$ip:${CameraStreamService.PORT}/stream"
            signalingClient?.notifyStreamReady(streamUrl)
            tvIpPort.text = "Kamera: $streamUrl"
        } else {
            signalingClient?.notifyStreamReady("")  // Boş URL = sadece WebSocket
            tvIpPort.text = "Kamera WebSocket üzerinden gönderiliyor"
        }
        updateStatus("📷 Kamera yayını aktif")
    }

    private fun stopCameraStream() {
        stopService(Intent(this, CameraStreamService::class.java))
        updateStatus("🟢 Ekran yayını aktif (kamera kapatıldı)")
    }

    private fun stopAllStreams() {
        stopService(Intent(this, ScreenStreamService::class.java))
        stopService(Intent(this, CameraStreamService::class.java))
        btnStopStream.isEnabled = false
        tvIpPort.text = ""
        updateStatus("⏹ Tüm yayınlar durduruldu")
    }

    private fun checkAccessibilityService() {
        val isEnabled = isAccessibilityServiceEnabled()
        tvAccessibility.text = if (isEnabled)
            "✅ Erişilebilirlik servisi aktif"
        else
            "⚠ Dokunma kontrolü için buraya tıklayın (Erişilebilirlik aktif et)"
    }

    private fun isAccessibilityServiceEnabled(): Boolean {
        val serviceName = "$packageName/${ControlReceiver::class.java.name}"
        val setting = android.provider.Settings.Secure.getString(
            contentResolver,
            android.provider.Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES
        ) ?: return false
        return setting.contains(serviceName)
    }

    private fun requestNotificationPermission() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS)
                != PackageManager.PERMISSION_GRANTED
            ) {
                notifPermLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
            }
        }
    }

    private fun getDeviceIp(): String {
        // Emülatör için her zamanki ADB port-forward senaryosu
        if (IS_EMULATOR) {
            // adb forward tcp:8080 tcp:8080
            // PC 127.0.0.1:8080 → emülatör 8080
            return "127.0.0.1"
        }

        return try {
            // Önce Wi‑Fi IP'sini dene
            val wm = applicationContext.getSystemService(WIFI_SERVICE) as android.net.wifi.WifiManager
            @Suppress("DEPRECATION")
            val wifiIp = Formatter.formatIpAddress(wm.connectionInfo.ipAddress)

            if (wifiIp != "0.0.0.0") {
                wifiIp
            } else {
                // Bazı cihazlarda WifiManager 0.0.0.0 döndürebiliyor, bu durumda
                // aktif IPv4 adresini network interface'lerden bul
                val interfaces = java.util.Collections.list(
                    java.net.NetworkInterface.getNetworkInterfaces()
                )
                for (intf in interfaces) {
                    val addrs = java.util.Collections.list(intf.inetAddresses)
                    for (addr in addrs) {
                        if (!addr.isLoopbackAddress && addr is java.net.Inet4Address) {
                            return addr.hostAddress
                        }
                    }
                }
                "0.0.0.0"
            }
        } catch (e: Exception) {
            "0.0.0.0"
        }
    }

    private fun updateStatus(msg: String) {
        Log.i(TAG, msg)
        tvStatus.text = msg
    }

    override fun onDestroy() {
        scope.cancel()
        signalingClient?.disconnect()
        super.onDestroy()
    }
}
