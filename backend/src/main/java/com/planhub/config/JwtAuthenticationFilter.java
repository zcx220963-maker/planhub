package com.planhub.config;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.web.authentication.WebAuthenticationDetailsSource;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.Collections;

@Component
public class JwtAuthenticationFilter extends OncePerRequestFilter {

    private final JwtUtil jwtUtil;

    public JwtAuthenticationFilter(JwtUtil jwtUtil) {
        this.jwtUtil = jwtUtil;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, 
                                   FilterChain filterChain) throws ServletException, IOException {
        try {
            String jwt = extractJwtFromRequest(request);
            
            System.out.println("===== JwtAuth Filter =====");
            System.out.println("Path: " + request.getRequestURI());
            System.out.println("JWT from request: " + (jwt != null ? "present (" + jwt.substring(0, Math.min(20, jwt.length())) + "...)" : "null"));
            
            if (StringUtils.hasText(jwt)) {
                boolean valid = jwtUtil.validateToken(jwt);
                System.out.println("JWT valid: " + valid);

                // 检查是否过期
                if (!valid) {
                    boolean expired = jwtUtil.isTokenExpired(jwt);
                    System.out.println("JWT expired: " + expired);
                    if (expired) {
                        try {
                            var claims = jwtUtil.extractClaims(jwt);
                            System.out.println("JWT expiration: " + claims.getExpiration());
                            System.out.println("Current time: " + new java.util.Date());
                        } catch (Exception e) {
                            System.out.println("Cannot parse JWT claims: " + e.getMessage());
                        }
                    }
                }
                
                if (valid) {
                    Long userId = jwtUtil.extractUserId(jwt);
                    String username = jwtUtil.extractUsername(jwt);
                    
                    System.out.println("UserId: " + userId + ", Username: " + username);
                    
                    UsernamePasswordAuthenticationToken authentication = 
                        new UsernamePasswordAuthenticationToken(
                            userId, 
                            null, 
                            Collections.singletonList(new SimpleGrantedAuthority("ROLE_USER"))
                        );
                    authentication.setDetails(new WebAuthenticationDetailsSource().buildDetails(request));
                    
                    SecurityContextHolder.getContext().setAuthentication(authentication);
                    System.out.println("Authentication set successfully");
                }
            } else {
                System.out.println("No JWT token - request will be anonymous");
            }
            System.out.println("===== End JwtAuth =====");
        } catch (Exception e) {
            System.err.println("ERROR in JwtAuth Filter: " + e.getMessage());
            e.printStackTrace();
        }
        
        filterChain.doFilter(request, response);
    }

    private String extractJwtFromRequest(HttpServletRequest request) {
        String bearerToken = request.getHeader("Authorization");
        System.out.println("Authorization header: " + bearerToken);
        if (StringUtils.hasText(bearerToken) && bearerToken.startsWith("Bearer ")) {
            return bearerToken.substring(7);
        }
        return null;
    }
}
