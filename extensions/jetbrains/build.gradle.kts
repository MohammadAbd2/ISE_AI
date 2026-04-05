plugins {
    id 'java'
    id 'org.jetbrains.kotlin.jvm' version '1.8.0'
    id 'org.jetbrains.intellij' version '1.13.0'
}

group 'com.ise.ai.copilot'
version '1.0.0'

repositories {
    mavenCentral()
}

dependencies {
    implementation 'org.jetbrains.kotlin:kotlin-stdlib-jdk8'
    implementation 'com.squareup.okhttp3:okhttp:4.10.0'
    implementation 'com.fasterxml.jackson.module:jackson-module-kotlin:2.14.0'
    implementation 'com.fasterxml.jackson.module:jackson-module-kotlin:2.14.0'
}

intellij {
    version.set('2023.1')
    type.set('IC') // IntelliJ Community
    plugins.set(listOf('com.intellij.modules.lang'))
}

patchPluginXml {
    sinceBuild.set('231')
    untilBuild.set('241.*')
}

signPlugin {
    certificateChain.set(System.getenv("CERTIFICATE_CHAIN"))
    privateKey.set(System.getenv("PRIVATE_KEY"))
    password.set(System.getenv("PRIVATE_KEY_PASSWORD"))
}

publishPlugin {
    token.set(System.getenv("PUBLISH_TOKEN"))
}

compileKotlin {
    kotlinOptions.jvmTarget = "17"
}

compileTestKotlin {
    kotlinOptions.jvmTarget = "17"
}
