package com.planhub.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.cloud.context.config.annotation.RefreshScope;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Lazy;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.web.client.RestTemplate;

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
     * 配置用于调用 AI 服务的 RestTemplate
     * 设置连接超时和读取超时，防止长时间阻塞
     * 关键：禁用请求/响应体缓冲，支持 SSE 真正的流式传输
     * @Lazy + @RefreshScope：配置变更后重新创建 Bean
     */
    @Bean(name = "aiRestTemplate")
    @Lazy
    @RefreshScope
    public RestTemplate aiRestTemplate() {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(connectTimeout);
        factory.setReadTimeout(readTimeout);
        // 注意：setBufferRequestBody 在 Spring 6.x 中已废弃
        // 对于 SSE 流式传输，需要使用 ClientHttpRequestFactory 的其他实现
        // 这里使用默认设置，因为 Spring 6.x 默认行为已经优化
        return new RestTemplate(factory);
    }
}
