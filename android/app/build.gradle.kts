plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

// Version kommt aus der Datei VERSION im Hauptordner (z. B. 1.0.0 -> versionCode 10000)
val glimraVersion = rootProject.file("../VERSION").readText().trim()
val glimraVersionCode = glimraVersion.split(".").map { it.toInt() }.let { (a, b, c) -> a * 10000 + b * 100 + c }

android {
    namespace = "de.glimraos.app"
    compileSdk = 34

    defaultConfig {
        applicationId = "de.glimraos.app"
        minSdk = 26
        targetSdk = 34
        versionCode = glimraVersionCode
        versionName = glimraVersion
    }

    // Feste Signatur über GitHub-Secrets (siehe tools/make-android-key.sh).
    // Ohne Secrets wird mit dem Debug-Schlüssel signiert – die APK ist trotzdem installierbar.
    val keystorePath: String? = System.getenv("GLIMRA_KEYSTORE")
    signingConfigs {
        create("glimra") {
            if (keystorePath != null) {
                storeFile = file(keystorePath)
                storePassword = System.getenv("GLIMRA_KEYSTORE_PASSWORD")
                keyAlias = System.getenv("GLIMRA_KEY_ALIAS") ?: "glimraapp"
                keyPassword = System.getenv("GLIMRA_KEY_PASSWORD") ?: System.getenv("GLIMRA_KEYSTORE_PASSWORD")
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            signingConfig = if (keystorePath != null) signingConfigs.getByName("glimra") else signingConfigs.getByName("debug")
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
    lint {
        abortOnError = false
        checkReleaseBuilds = false
    }
}
