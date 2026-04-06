plugins {
    id("java")
    id("org.jetbrains.kotlin.jvm") version "1.9.23"
    id("org.jetbrains.intellij") version "1.13.3"
}

group = "com.ise.ai.copilot"
version = "1.0.0"

repositories {
    mavenCentral()
}

java {
    sourceCompatibility = JavaVersion.VERSION_17
    targetCompatibility = JavaVersion.VERSION_17
}

dependencies {
    implementation("org.jetbrains.kotlin:kotlin-stdlib-jdk8")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-core:1.8.0")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-jdk8:1.8.0")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("com.fasterxml.jackson.module:jackson-module-kotlin:2.17.0")
}

intellij {
    version.set("2024.1")
    type.set("IC")
    plugins.set(listOf())
}

tasks {
    patchPluginXml {
        sinceBuild.set("232")
        untilBuild.set("261.*")
    }

    compileKotlin {
        kotlinOptions.jvmTarget = "17"
        kotlinOptions.freeCompilerArgs = listOf("-Xjvm-default=all")
    }

    compileTestKotlin {
        kotlinOptions.jvmTarget = "17"
    }

    signPlugin { enabled = false }
    publishPlugin { enabled = false }
}
