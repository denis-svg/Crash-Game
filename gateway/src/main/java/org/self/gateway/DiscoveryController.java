package org.self.gateway;

import org.springframework.http.HttpEntity;
import org.springframework.http.HttpMethod;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.RestTemplate;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/discovery")
public class DiscoveryController {

    // In-memory service registry, mapping service types to their lists of URLs
    private final Map<String, ArrayList<String>> services = new HashMap<>();

    @PostMapping("/register")
    public String registerService(@RequestBody Map<String, String> request) {
        // Extract service type and URL from the request map
        String serviceUrl = request.get("serviceUrl");
        String serviceType = request.get("serviceType");  // New field for service type

        // Ensure the list for the service type exists
        services.putIfAbsent(serviceType, new ArrayList<>());

        // Add the service URL to the appropriate list
        services.get(serviceType).add(serviceUrl);

        // Notify the gateway about the new service
        request.put("action", "register");
        notifyGateway(request);

        return "Service registered: " + serviceUrl;
    }

    @DeleteMapping("/deregister/{serviceType}/{serviceUrl}")
    public String deregisterService(@PathVariable String serviceType, @PathVariable String serviceUrl) {
        List<String> urls = services.get(serviceType);
        if (urls != null) {
            urls.removeIf(url -> url.equals(serviceUrl)); // Assuming serviceName is the URL for simplicity
            Map<String, String> request = new HashMap<>();
            request.put("serviceUrl", serviceUrl);
            request.put("serviceType", serviceType);
            request.put("action", "deregister");
            notifyGateway(request);
        }
        return "Service deregistered: " + serviceUrl;
    }

    @GetMapping("/services")
    public Map<String, ArrayList<String>> getServices() {
        return services;
    }

    private void notifyGateway(Map<String, String> request) {
        String gatewayUrl = "http://gateway:8080/gateway/cache";
        RestTemplate restTemplate = new RestTemplate();

        String action = request.get("action");
        if ("deregister".equals(action)) {
            try {
                restTemplate.exchange(gatewayUrl, HttpMethod.DELETE, new HttpEntity<>(request), String.class);
            } catch (Exception e) {
                System.out.println("Failed to notify gateway: " + e.getMessage());
            }
        } else {
            try {
                restTemplate.postForEntity(gatewayUrl, request, String.class);
            } catch (Exception e) {
                System.out.println("Failed to notify gateway: " + e.getMessage());
            }
        }
    }
}