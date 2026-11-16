// Builds the tour with `./gradlew installDist`, compiling the Java that
// `temper build -b java` generates at the repo's top along with it, and
// runs it with `build/install/tour/bin/tour ARGS...` (or `./gradlew run
// --args="ARGS..."`).

plugins {
    application
}

val temperOut = file("../../../temper.out/java")

sourceSets {
    main {
        java {
            for (library in listOf("temper-core", "argmas")) {
                srcDir(temperOut.resolve("$library/src/main/java"))
            }
        }
    }
}

tasks.withType<JavaCompile> {
    options.encoding = "UTF-8"
    options.compilerArgs.add("-nowarn")
}

application {
    applicationName = "tour"
    mainClass = "Tour"
    // Java prints in the locale's encoding, which may not be UTF-8.
    applicationDefaultJvmArgs = listOf("-Dstdout.encoding=UTF-8", "-Dstderr.encoding=UTF-8")
}
