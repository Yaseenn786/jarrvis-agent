#!/bin/bash
LOG=agent/test.log

cat >> $LOG << 'EOF'
[INFO] Copying 21 resources from src/main/resources to target/classes
[INFO] --- compiler:3.14.1:compile (default-compile) @ Attendance ---
[INFO] Recompiling the module because of changed source code.
[INFO] Compiling 162 source files with javac [debug parameters release 17] to target/classes
[INFO] -------------------------------------------------------------
[ERROR] COMPILATION ERROR :
[INFO] -------------------------------------------------------------
[ERROR] /Users/mohamadyaseen/Desktop/Attendance/src/main/java/com/Clock_Backend/Attendance/service/PayMultiplierConfigService.java:[14,2] cannot find symbol
[ERROR]   symbol: class Slf4j
[ERROR] /Users/mohamadyaseen/Desktop/Attendance/src/main/java/com/Clock_Backend/Attendance/service/PayMultiplierConfigService.java:[16,2] cannot find symbol
[ERROR]   symbol: class RequiredArgsConstructor
[ERROR] /Users/mohamadyaseen/Desktop/Attendance/src/main/java/com/Clock_Backend/Attendance/service/PayMultiplierConfigService.java:[19,19] cannot find symbol
[ERROR]   symbol:   class PayMultiplierConfigRepository
[INFO] 3 errors
[INFO] BUILD FAILURE
[ERROR] Failed to execute goal org.apache.maven.plugins:maven-compiler-plugin:3.14.1:compile (default-compile) on project Attendance: Compilation failure
[ERROR] To see the full stack trace of the errors, re-run Maven with the -e switch.
EOF