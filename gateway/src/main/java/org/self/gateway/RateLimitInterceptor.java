package org.self.gateway;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;

import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.TimeUnit;

@Component
public class RateLimitInterceptor implements HandlerInterceptor {

    private final long RATE_LIMIT = 5; // Number of requests allowed
    private final long TIME_WINDOW = TimeUnit.SECONDS.toMillis(10); // Time window in milliseconds
    private final ConcurrentHashMap<String, RequestCounter> requestCounts = new ConcurrentHashMap<>();

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) throws Exception {
        String clientIp = request.getRemoteAddr();
        String requestUri = request.getRequestURI();

        // Check if the request URI starts with "/user/"
        if (requestUri.startsWith("/gateway/user/")) {
            RequestCounter counter = requestCounts.computeIfAbsent(clientIp, k -> new RequestCounter());

            if (counter.isWithinLimit(RATE_LIMIT, TIME_WINDOW)) {
                return true; // Allow request
            } else {
                response.setStatus(429); // HTTP 429
                return false; // Block request
            }
        }
        return true; // Allow other requests
    }

    private static class RequestCounter {
        private long lastRequestTime;
        private int requestCount;

        public boolean isWithinLimit(long rateLimit, long timeWindow) {
            long now = System.currentTimeMillis();
            if (now - lastRequestTime > timeWindow) {
                // Reset count and timestamp
                requestCount = 1;
                lastRequestTime = now;
                return true;
            } else if (requestCount < rateLimit) {
                requestCount++;
                return true;
            }
            return false; // Limit exceeded
        }
    }
}
