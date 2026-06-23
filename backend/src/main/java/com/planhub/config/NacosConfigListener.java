package com.planhub.config;

import com.alibaba.cloud.nacos.NacosConfigManager;
import com.alibaba.nacos.api.config.ConfigService;
import com.alibaba.nacos.api.config.listener.Listener;
import jakarta.annotation.PostConstruct;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Configuration;

import java.util.concurrent.Executor;
import java.util.concurrent.Executors;

/**
 * Nacos 配置变更监听器
 *
 * 用途：
 * 1. 监听 Nacos 配置中心的配置变化，便于调试和记录
 * 2. 关键配置（如 JWT 密钥、AI 服务地址）变更时可立即生效
 *
 * 使用 @RefreshScope 的 Bean 会在配置变更后自动刷新
 *
 * 使用方法：
 *  - 在 Nacos 控制台修改配置 → 点击发布 → 应用自动刷新 @RefreshScope 的 Bean
 *  - 无需重启应用
 *
 * 注意：此类只在 spring.cloud.nacos.config.enabled=true 时才会加载
 *       如果未启用 Nacos 配置中心，此类不会被创建，避免 Bean 注入失败
 */
@Configuration
@ConditionalOnProperty(prefix = "spring.cloud.nacos.config", name = "enabled", havingValue = "true")
@Slf4j
public class NacosConfigListener {

    @Autowired
    private NacosConfigManager nacosConfigManager;

    @Value("${spring.cloud.nacos.config.group:DEFAULT_GROUP}")
    private String group;

    @Value("${spring.cloud.nacos.config.file-extension:yaml}")
    private String fileExtension;

    @Value("${spring.application.name:planhub-backend}")
    private String appName;

    // 线程池：异步执行配置变更回调
    private final Executor executor = Executors.newFixedThreadPool(1, r -> {
        Thread t = new Thread(r, "nacos-config-listener");
        t.setDaemon(true);
        return t;
    });

    @PostConstruct
    public void init() {
        try {
            ConfigService configService = nacosConfigManager.getConfigService();
            if (configService == null) {
                log.warn("[Nacos] ConfigService 未初始化，跳过监听器注册");
                return;
            }

            // 主配置文件：{appName}.{fileExtension}
            String mainDataId = appName + "." + fileExtension;
            registerListener(configService, mainDataId, group);

            // 扩展配置文件（与 bootstrap.yml 中 extension-configs 对应）
            registerListener(configService, "planhub-datasource.yaml", group);
            registerListener(configService, "planhub-jwt.yaml", group);
            registerListener(configService, "planhub-ai.yaml", group);
            registerListener(configService, "planhub-common.yaml", group);

            log.info("[Nacos] 配置变更监听器注册成功，dataIds: planhub-backend.yaml, planhub-datasource.yaml, planhub-jwt.yaml, planhub-ai.yaml, planhub-common.yaml");

        } catch (Exception e) {
            log.warn("[Nacos] 配置监听器初始化失败（不影响业务，可能 Nacos 未启动或未启用配置中心）: {}", e.getMessage());
        }
    }

    private void registerListener(ConfigService configService, String dataId, String group) {
        try {
            configService.addListener(dataId, group, new Listener() {
                @Override
                public Executor getExecutor() {
                    return executor;
                }

                @Override
                public void receiveConfigInfo(String configInfo) {
                    // 安全考虑：不打印完整配置内容（可能包含密码），仅打印前 200 字符
                    String preview = configInfo == null ? "null" :
                            configInfo.length() > 200 ? configInfo.substring(0, 200) + "..." : configInfo;
                    log.info("[Nacos] 配置变更: dataId={}, group={}, 内容预览={}", dataId, group, preview);
                }
            });
        } catch (Exception e) {
            log.warn("[Nacos] 注册监听器失败 dataId={}: {}", dataId, e.getMessage());
        }
    }
}
