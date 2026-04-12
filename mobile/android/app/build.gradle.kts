import java.io.File
import java.util.Properties
import org.gradle.api.GradleException

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

fun resolvedStoreFile(path: String): File {
    val configuredFile = file(path)
    return if (configuredFile.isAbsolute) configuredFile else rootProject.file(path)
}

val releaseStoreFilePath = releaseSigningValue("storeFile", "ANDROID_KEYSTORE_PATH")
val releaseStorePassword = releaseSigningValue("storePassword", "ANDROID_KEYSTORE_PASSWORD")
val releaseKeyAlias = releaseSigningValue("keyAlias", "ANDROID_KEY_ALIAS")
val releaseKeyPassword = releaseSigningValue("keyPassword", "ANDROID_KEY_PASSWORD")

val releaseStoreFile = releaseStoreFilePath
    ?.takeIf { it.isNotBlank() }
    ?.let(::resolvedStoreFile)

val releaseSigningInputsComplete = releaseStoreFile != null &&
    releaseStoreFile.exists() &&
    !releaseStorePassword.isNullOrBlank() &&
    !releaseKeyAlias.isNullOrBlank() &&
    !releaseKeyPassword.isNullOrBlank()

val releaseTasksRequested = gradle.startParameter.taskNames
    .map { it.lowercase() }
    .any { taskName ->
        "release" in taskName || "bundle" in taskName || "publish" in taskName
    }

android {
    namespace = "com.ecommerce.app"
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
            if (releaseSigningInputsComplete) {
                storeFile = releaseStoreFile
                storePassword = releaseStorePassword
                keyAlias = releaseKeyAlias
                keyPassword = releaseKeyPassword
            }
        }
    }

    defaultConfig {
        applicationId = "com.ecommerce.app"
        minSdk = flutter.minSdkVersion
        targetSdk = flutter.targetSdkVersion
        versionCode = flutter.versionCode
        versionName = flutter.versionName
    }

    flavorDimensions += "environment"
    productFlavors {
        create("production") {
            dimension = "environment"
        }
    }

    buildTypes {
        debug {
            signingConfig = signingConfigs.getByName("debug")
            applicationIdSuffix = ".debug"
            versionNameSuffix = "-debug"
        }

        create("staging") {
            initWith(getByName("debug"))
            applicationIdSuffix = ".staging"
            versionNameSuffix = "-staging"
            matchingFallbacks += listOf("debug")
            signingConfig = signingConfigs.getByName("debug")
        }

        release {
            if (!releaseSigningInputsComplete && releaseTasksRequested) {
                throw GradleException(
                    "Release signing is not configured. " +
                        "Set ANDROID_KEYSTORE_PATH/ANDROID_KEYSTORE_PASSWORD/" +
                        "ANDROID_KEY_ALIAS/ANDROID_KEY_PASSWORD or provide android/key.properties."
                )
            }
            signingConfig = signingConfigs.getByName("release")
        }
    }
}

flutter {
    source = "../.."
}
