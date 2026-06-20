package com.planhub;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
@MapperScan("com.planhub.mapper")
public class PlanHubApplication {
    public static void main(String[] args) {
        SpringApplication.run(PlanHubApplication.class, args);
    }
}
