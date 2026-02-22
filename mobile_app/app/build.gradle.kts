plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
}

android {
    namespace = "com.remotecontrol"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.remotecontrol"
        minSdk = 26
        targetSdk = 34
        versionCode = 1
        versionName = "1.0"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    buildFeatures {
        viewBinding = true
    }
}

dependencies {
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.appcompat)
    implementation(libs.material)
    implementation(libs.constraintlayout)

    // CameraX
    implementation(libs.camera.core)
    implementation(libs.camera.camera2)
    implementation(libs.camera.lifecycle)
    implementation(libs.camera.view)

    // OkHttp (WebSocket)
    implementation(libs.okhttp)

    // Coroutines
    implementation(libs.coroutines.android)

    // NanoHTTPD (MJPEG HTTP sunucu)
    implementation(libs.nanohttpd)

    // Lifecycle Service (CameraStreamService için LifecycleService)
    implementation(libs.lifecycle.service)
}
