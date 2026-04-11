import java.util.Properties

plugins {
    id("com.android.application")
    id("kotlin-android")
    // The Flutter Gradle Plugin must be applied after the Android and Kotlin Gradle plugins.
    id("dev.flutter.flutter-gradle-plugin")
}

val releaseSigningProperties = Properties().apply {
    val candidateFiles = listOf(
        rootProject.file("key.properties"),
        rootProject.file("release-signing.properties"),
    )

    candidateFiles.firstOrNull { it.exists() }?.inputStream()?.use { load(it) }
}

fun releaseSigningValue(propertyKey: String, envKey: String): String? {
    return releaseSigningProperties.getProperty(propertyKey)
        ?: System.getenv(envKey)
}

android {
    namespace = "com.ecommerce.mobile"
    compileSdk = flutter.compileSdkVersion
    ndkVersion = flutter.ndkVersion

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = JavaVersion.VERSION_17.toString()
    }

    signingConfigs {
        create("release") {
            val storeFilePath = releaseSigningValue("storeFile", "ANDROID_KEYSTORE_PATH")

            if (!storeFilePath.isNullOrBlank()) {
                storeFile = file(storeFilePath)
            }

            storePassword = releaseSigningValue("storePassword", "ANDROID_KEYSTORE_PASSWORD")
            keyAlias = releaseSigningValue("keyAlias", "ANDROID_KEY_ALIAS")
            keyPassword = releaseSigningValue("keyPassword", "ANDROID_KEY_PASSWORD")
        }
    }

    defaultConfig {
        applicationId = "com.ecommerce.mobile"
        minSdk = flutter.minSdkVersion
        targetSdk = flutter.targetSdkVersion
        versionCode = flutter.versionCode
        versionName = flutter.versionName
    }

    buildTypes {
        debug {
            signingConfig = signingConfigs.getByName("debug")
        }

        release {
            signingConfig = signingConfigs.getByName("release")
        }
    }
}

flutter {
    source = "../.."
}
