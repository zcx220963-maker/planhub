package com.planhub.config;

import io.netty.channel.ChannelOption;
import io.netty.handler.timeout.ReadTimeoutHandler;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.cloud.context.config.annotation.RefreshScope;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Lazy;
import org.springframework.http.client.reactive.ReactorClientHttpConnector;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.netty.http.client.HttpClient;

import java.time.Duration;
import java.util.concurrent.TimeUnit;

/**
 * AI 服务配置
 * 
 * 配置 Java 后端与 Python AI 服务之间的通信：
 * 1. Python AI 服务作为内部服务运行在 127.0.0.1:8000
 * 2. Java 作为安全网关，验证用户 JWT 后转发请求到 Python
 * 3. Java 每次调用 Python 时携带内部密钥 (X-Internal-Api-Secret)
 * 4. Python 只信任携带正确内部密钥的请求
 * 
 * 关键：@RefreshScope 让 Nacos 配置变更后自动刷新 Bean
 */
@Configuration
@RefreshScope
public class AiServiceConfig {

    @Value("${ai.service.url}")
    private String aiServiceUrl;

    @Value("${ai.service.internal-secret}")
    private String internalSecret;

    @Value("${ai.service.internal-secret-header}")
    private String internalSecretHeader;

    @Value("${ai.service.connect-timeout:5000}")
    private int connectTimeout;

    @Value("${ai.service.read-timeout:300000}")
    private int readTimeout;

    public String getAiServiceUrl() {
        return aiServiceUrl;
    }

    public String getInternalSecret() {
        return internalSecret;
    }

    public String getInternalSecretHeader() {
        return internalSecretHeader;
    }

    public int getConnectTimeout() {
        return connectTimeout;
    }

    public int getReadTimeout() {
        return readTimeout;
    }

    /**
     * 配置用于调用 AI 服务的 RestTemplate（非流式请求用）
     */
    @Bean(name = "aiRestTemplate")
    @Lazy
    @RefreshScope
    public RestTemplate aiRestTemplate() {
        var factory = new org.springframework.http.client.SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(connectTimeout);
        factory.setReadTimeout(readTimeout);
        return new RestTemplate(factory);
    }

    /**
     * 配置 WebClient（用于 SSE 流式透传）
     * 使用 Reactor Netty HttpClient，支持真正的异步非阻塞流式传输
     */
    @Bean(name = "aiWebClient")
    @Lazy
    @RefreshScope
    @SuppressWarnings("null")
    public WebClient aiWebClient() {
        HttpClient httpClient = HttpClient.create()
                .option(ChannelOption.CONNECT_TIMEOUT_MILLIS, connectTimeout)
                .responseTimeout(Duration.ofMillis(readTimeout))
                .doOnConnected(conn -> conn.addHandlerLast(
                        new ReadTimeoutHandler(readTimeout, TimeUnit.MILLISECONDS)));

        return WebClient.builder()
                .baseUrl(aiServiceUrl)
                .clientConnector(new ReactorClientHttpConnector(httpClient))
                .build();
    }
}
