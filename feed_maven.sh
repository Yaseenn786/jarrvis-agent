#!/bin/bash
LOG=agent/test.log

cat >> $LOG << 'EOF'
mohamadyaseen@Mohamads-MacBook-Air hub % ./run.sh
[INFO] Scanning for projects...
[INFO] 
[INFO] --------------------------< com.jarrvis:hub >---------------------------
[INFO] Building  0.0.1-SNAPSHOT
[INFO]   from pom.xml
[INFO] --------------------------------[ jar ]---------------------------------
[INFO] 
[INFO] >>> spring-boot:4.1.0:run (default-cli) > test-compile @ hub >>>
[INFO] 
[INFO] --- resources:3.5.0:resources (default-resources) @ hub ---
[INFO] Copying 1 resource from src/main/resources to target/classes
[INFO] Copying 0 resource from src/main/resources to target/classes
[INFO] 
[INFO] --- compiler:3.15.0:compile (default-compile) @ hub ---
[INFO] Recompiling the module because of changed source code.
[INFO] Compiling 29 source files with javac [debug parameters release 17] to target/classes
[INFO] /Users/mohamadyaseen/Desktop/hub/src/main/java/com/jarrvis/hub/service/ChatService.java: Some input files use unchecked or unsafe operations.
[INFO] /Users/mohamadyaseen/Desktop/hub/src/main/java/com/jarrvis/hub/service/ChatService.java: Recompile with -Xlint:unchecked for details.
[INFO] 
[INFO] --- resources:3.5.0:testResources (default-testResources) @ hub ---
[INFO] skip non existing resourceDirectory /Users/mohamadyaseen/Desktop/hub/src/test/resources
[INFO] 
[INFO] --- compiler:3.15.0:testCompile (default-testCompile) @ hub ---
[INFO] Recompiling the module because of changed dependency.
[INFO] Compiling 1 source file with javac [debug parameters release 17] to target/test-classes
[INFO] 
[INFO] <<< spring-boot:4.1.0:run (default-cli) < test-compile @ hub <<<
[INFO] 
[INFO] 
[INFO] --- spring-boot:4.1.0:run (default-cli) @ hub ---
[INFO] Attaching agents: []

  .   ____          _            __ _ _
 /\\ / ___'_ __ _ _(_)_ __  __ _ \ \ \ \
( ( )\___ | '_ | '_| | '_ \/ _` | \ \ \ \
 \\/  ___)| |_)| | | | | || (_| |  ) ) ) )
  '  |____| .__|_| |_|_| |_\__, | / / / /
 =========|_|==============|___/=/_/_/_/

 :: Spring Boot ::                (v4.1.0)

2026-07-18T16:27:24.323+01:00  INFO 63270 --- [           main] com.jarrvis.hub.HubApplication           : Starting HubApplication using Java 17.0.14 with PID 63270 (/Users/mohamadyaseen/Desktop/hub/target/classes started by mohamadyaseen in /Users/mohamadyaseen/Desktop/hub)
2026-07-18T16:27:24.326+01:00  INFO 63270 --- [           main] com.jarrvis.hub.HubApplication           : No active profile set, falling back to 1 default profile: "default"
2026-07-18T16:27:24.772+01:00  INFO 63270 --- [           main] .s.d.r.c.RepositoryConfigurationDelegate : Bootstrapping Spring Data JPA repositories in DEFAULT mode.
2026-07-18T16:27:24.883+01:00  INFO 63270 --- [           main] .s.d.r.c.RepositoryConfigurationDelegate : Finished Spring Data repository scanning in 105 ms. Found 6 JPA repository interfaces.
2026-07-18T16:27:25.230+01:00  INFO 63270 --- [           main] o.s.boot.tomcat.TomcatWebServer          : Tomcat initialized with port 8081 (http)
2026-07-18T16:27:25.241+01:00  INFO 63270 --- [           main] o.apache.catalina.core.StandardService   : Starting service [Tomcat]
2026-07-18T16:27:25.241+01:00  INFO 63270 --- [           main] o.apache.catalina.core.StandardEngine    : Starting Servlet engine: [Apache Tomcat/11.0.22]
2026-07-18T16:27:25.277+01:00  INFO 63270 --- [           main] b.w.c.s.WebApplicationContextInitializer : Root WebApplicationContext: initialization completed in 910 ms
2026-07-18T16:27:25.400+01:00  INFO 63270 --- [           main] org.hibernate.orm.jpa                    : HHH008540: Processing PersistenceUnitInfo [name: default]
2026-07-18T16:27:25.439+01:00  INFO 63270 --- [           main] org.hibernate.orm.core                   : HHH000001: Hibernate ORM core version 7.4.1.Final
2026-07-18T16:27:25.722+01:00  INFO 63270 --- [           main] o.s.o.j.p.SpringPersistenceUnitInfo      : No LoadTimeWeaver setup: ignoring JPA class transformer
2026-07-18T16:27:25.745+01:00  INFO 63270 --- [           main] com.zaxxer.hikari.HikariDataSource       : HikariPool-1 - Starting...
2026-07-18T16:27:25.884+01:00  INFO 63270 --- [           main] com.zaxxer.hikari.pool.HikariPool        : HikariPool-1 - Added connection org.postgresql.jdbc.PgConnection@24e2355c
2026-07-18T16:27:25.885+01:00  INFO 63270 --- [           main] com.zaxxer.hikari.HikariDataSource       : HikariPool-1 - Start completed.
2026-07-18T16:27:25.957+01:00  INFO 63270 --- [           main] org.hibernate.orm.connections.pooling    : HHH10001005: Database info:
        Database JDBC URL [jdbc:postgresql://localhost:5432/jarrvis_hub]
        Database driver: PostgreSQL JDBC Driver
        Database dialect: PostgreSQLDialect
        Database version: 17.4
        Default catalog/schema: jarrvis_hub/public
        Autocommit mode: undefined/unknown
        Isolation level: READ_COMMITTED [default READ_COMMITTED]
        JDBC fetch size: none
        Pool: DataSourceConnectionProvider
        Minimum pool size: undefined/unknown
        Maximum pool size: undefined/unknown
2026-07-18T16:27:26.638+01:00  INFO 63270 --- [           main] org.hibernate.orm.core                   : HHH000489: No JTA platform available (set 'hibernate.transaction.jta.platform' to enable JTA platform integration)
2026-07-18T16:27:26.769+01:00  INFO 63270 --- [           main] j.LocalContainerEntityManagerFactoryBean : Initialized JPA EntityManagerFactory for persistence unit 'default'
2026-07-18T16:27:26.825+01:00  INFO 63270 --- [           main] o.s.d.j.r.query.QueryEnhancerFactories   : Hibernate is in classpath; If applicable, HQL parser will be used.
2026-07-18T16:27:27.824+01:00  INFO 63270 --- [           main] o.s.boot.tomcat.TomcatWebServer          : Tomcat started on port 8081 (http) with context path '/'
2026-07-18T16:27:27.830+01:00  INFO 63270 --- [           main] com.jarrvis.hub.HubApplication           : Started HubApplication in 3.986 seconds (process running for 4.277)
2026-07-18T16:27:27.892+01:00  INFO 63270 --- [nio-8081-exec-2] o.a.c.c.C.[Tomcat].[localhost].[/]       : Initializing Spring DispatcherServlet 'dispatcherServlet'
2026-07-18T16:27:27.893+01:00  INFO 63270 --- [nio-8081-exec-2] o.s.web.servlet.DispatcherServlet        : Initializing Servlet 'dispatcherServlet'
2026-07-18T16:27:27.894+01:00  INFO 63270 --- [nio-8081-exec-2] o.s.web.servlet.DispatcherServlet        : Completed initialization in 1 ms



EOF