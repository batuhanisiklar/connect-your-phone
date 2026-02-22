package com.remotecontrol

import android.util.Log
import kotlinx.coroutines.*
import okhttp3.*
import okio.ByteString
import org.json.JSONObject
import java.util.concurrent.TimeUnit
import kotlin.random.Random

/**
 * Signaling sunucusuyla WebSocket üzerinden haberleşir.
 * - 6 haneli rastgele bir oturum kodu üretir
 * - Kodu sunucuya kaydeder
 * - PC eşleştiğinde callback tetikler
 * - Relay üzerinden gelen komutları iletir
 */
class SignalingClient(
    private val serverUrl: String,
    private val onPaired: (streamPort: Int) -> Unit,
    private val onCommand: (action: String, params: Map<String, Any>) -> Unit,
    private val onDisconnected: () -> Unit,
) {
    companion object {
        private const val TAG = "SignalingClient"
        fun generateCode(): String = (100_000..999_999).random().toString()

        /** Diğer servislerden frame göndermek için erişilebilir instance */
        var instance: SignalingClient? = null
    }

    val sessionCode: String = generateCode()

    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private val client = OkHttpClient.Builder()
        .pingInterval(20, TimeUnit.SECONDS)
        .readTimeout(0, TimeUnit.MILLISECONDS)  // WebSocket için timeout kapatılır
        .build()

    private var ws: WebSocket? = null

    fun connect() {
        instance = this
        val request = Request.Builder().url(serverUrl).build()
        ws = client.newWebSocket(request, object : WebSocketListener() {

            override fun onOpen(webSocket: WebSocket, response: Response) {
                Log.i(TAG, "Connected to signaling server, code=$sessionCode")
                // Telefon olarak kayıt
                val msg = JSONObject().apply {
                    put("type", "register")
                    put("code", sessionCode)
                    put("role", "phone")
                }
                webSocket.send(msg.toString())
            }

            override fun onMessage(webSocket: WebSocket, text: String) {
                Log.d(TAG, "Message: $text")
                try {
                    val json = JSONObject(text)
                    when (json.getString("type")) {
                        "registered" -> Log.i(TAG, "Registered with code=$sessionCode")

                        "paired" -> {
                            Log.i(TAG, "Paired with PC!")
                            // Stream başladıktan sonra stream_info gönder
                            scope.launch {
                                delay(500)
                                onPaired(8080) // NanoHTTPD 8080 portunda dinler
                            }
                        }

                        "command" -> {
                            val action = json.optString("action", "")
                            val params = mutableMapOf<String, Any>()
                            json.keys().forEach { key ->
                                if (key != "type" && key != "action") {
                                    params[key] = json.get(key)
                                }
                            }
                            onCommand(action, params)
                        }

                        "peer_disconnected" -> {
                            Log.i(TAG, "PC disconnected")
                            onDisconnected()
                        }

                        "error" -> Log.e(TAG, "Server error: ${json.optString("message")}")
                    }
                } catch (e: Exception) {
                    Log.e(TAG, "Parse error: $e")
                }
            }

            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                Log.e(TAG, "WS failure: $t")
                onDisconnected()
            }

            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                Log.i(TAG, "WS closed: $code $reason")
                onDisconnected()
            }
        })
    }

    /**
     * Stream başladıktan sonra PC'ye HTTP stream URL'sini iletir.
     * PC, relay signaling sunucusu üzerinden bu URL'yi alır ve MJPEG istemcisini başlatır.
     * 
     * NOT: İnternet üzerinden çalışmak için telefon IP'si
     * ngrok tüneli veya benzeri ile halka açık olmalıdır.
     * Bu implementasyonda URL doğrudan gönderilir; production'da
     * bir relay mekanizması gerekir.
     */
    /**
     * Kamera/ekran JPEG frame'ini Base64 JSON olarak PC'ye relay eder.
     * Port forwarding gerektirmez — WebSocket üzerinden gider.
     */
    fun sendFrame(jpeg: ByteArray) {
        val currentWs = ws
        if (currentWs == null) {
            Log.w(TAG, "WebSocket null - frame gönderilemedi")
            return
        }
        try {
            val b64 = android.util.Base64.encodeToString(jpeg, android.util.Base64.NO_WRAP)
            val msg = JSONObject().apply {
                put("type", "frame")
                put("data", b64)
            }
            currentWs.send(msg.toString())
            Log.d(TAG, "Frame gönderildi: ${jpeg.size} bytes -> ${b64.length} chars base64")
        } catch (e: Exception) {
            Log.e(TAG, "Frame gönderme hatası: $e", e)
        }
    }

    fun notifyStreamReady(publicUrl: String) {
        val msg = JSONObject().apply {
            put("type", "stream_info")
            put("url", publicUrl)
        }
        ws?.send(msg.toString())
        Log.i(TAG, "Sent stream_info: $publicUrl")
    }

    fun disconnect() {
        ws?.close(1000, "Client disconnect")
        scope.cancel()
        client.dispatcher.executorService.shutdown()
    }
}
