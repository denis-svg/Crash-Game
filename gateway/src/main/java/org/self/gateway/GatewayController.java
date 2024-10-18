package org.self.gateway;

import org.springframework.http.*;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestTemplate;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/gateway")
public class GatewayController {

    // In-memory service registry, mapping service types to their lists of URLs
    private final Map<String, ArrayList<String>> services = new HashMap<>();

    // Round-robin counters for each service type
    private final Map<String, Integer> roundRobinCounters = new HashMap<>();

    private final RestTemplate restTemplate;

    public GatewayController() {
        this.restTemplate = this.createRestTemplate();
    }

    private RestTemplate createRestTemplate() {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(2000); // Set connect timeout (in milliseconds)
        factory.setReadTimeout(5000); // Set read timeout (in milliseconds)
        return new RestTemplate(factory);
    }

    @PostMapping("/cache")
    public ResponseEntity<String> updateCache(@RequestBody Map<String, String> request) {
        // Extract service type and URL from the request
        String serviceUrl = request.get("serviceUrl");
        String serviceType = request.get("serviceType");

        // Ensure the list for the service type exists
        services.putIfAbsent(serviceType, new ArrayList<>());

        // Add the service URL to the appropriate list
        services.get(serviceType).add(serviceUrl);

        // Initialize round-robin counter for the service type if not present
        roundRobinCounters.putIfAbsent(serviceType, 0);

        return ResponseEntity.ok("Service cache updated: " + serviceUrl);
    }

    private String getNextServiceUrl(String serviceType) {
        List<String> serviceUrls = services.get(serviceType);

        if (serviceUrls == null || serviceUrls.isEmpty()) {
            throw new IllegalStateException("No services registered for: " + serviceType);
        }

        // Get the current counter value for the service type
        int currentIndex = roundRobinCounters.get(serviceType);

        // Get the next URL using the counter and wrap around if needed
        String nextUrl = serviceUrls.get(currentIndex);

        // Update the counter, wrapping around if necessary
        roundRobinCounters.put(serviceType, (currentIndex + 1) % serviceUrls.size());

        return nextUrl;
    }

    @DeleteMapping("/cache")
    public ResponseEntity<String> deregisterService(@RequestBody Map<String, String> request) {
        String serviceUrl = request.get("serviceUrl");
        String serviceType = request.get("serviceType");
        List<String> urls = services.get(serviceType);

        if (urls != null) {
            boolean removed = urls.remove(serviceUrl); // Remove the service URL
            if (removed) {
                return ResponseEntity.ok("Service deregistered: " + serviceUrl);
            }
        }
        return ResponseEntity.status(HttpStatus.NOT_FOUND).body("Service not found: " + serviceUrl);
    }

    @GetMapping("/cache")
    public Map<String, ArrayList<String>> getServices() {
        return services;
    }

    @GetMapping("/status")
    public ResponseEntity<Map<String, Object>> status() {
        Map<String, Object> statusResponse = new HashMap<>();
        List<String> workingServices = new ArrayList<>();

        // Iterate over all service types in the registry
        for (Map.Entry<String, ArrayList<String>> serviceEntry : services.entrySet()) {
            String serviceType = serviceEntry.getKey();
            ArrayList<String> serviceUrls = serviceEntry.getValue();

            // Check each service URL for the current service type
            for (String serviceUrl : serviceUrls) {
                try {
                    // Ping the service status endpoint
                    String statusUrl;
                    if (serviceType.equals("game_service")) {
                        statusUrl = serviceUrl + "/game/v1/status";
                    } else {
                        statusUrl = serviceUrl + "/user/v1/status";
                    }
                    ResponseEntity<String> response = restTemplate.getForEntity(statusUrl, String.class);

                    // If the service responds with HTTP 200 OK, mark it as working
                    if (response.getStatusCode() == HttpStatus.OK) {
                        workingServices.add(serviceType + ": " + serviceUrl);
                    }
                } catch (RestClientException e) {
                    // If any service fails, return an error for that service
                    statusResponse.put("message", "Some services are down");
                    statusResponse.put("workingServices", workingServices);
                    statusResponse.put("failedService", serviceType + ": " + serviceUrl);

                    return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(statusResponse);
                }
            }
        }

        // If all services are working, return the list of working services and a success message
        statusResponse.put("message", "All services are up and running");
        statusResponse.put("workingServices", workingServices);

        return ResponseEntity.ok(statusResponse);
    }

    @GetMapping("/user/v1/status")
    public ResponseEntity<String> user_status() {
        String url = getNextServiceUrl("auth_service");
        // Make the HTTP request and get the response
        return getStringResponseEntity(url + "/user/v1/status");
    }

    @GetMapping("/game/v1/status")
    public ResponseEntity<String> game_status() {
        String url = getNextServiceUrl("game_service");


        // Make the HTTP request and get the response
        return getStringResponseEntity(url + "/game/v1/status");
    }

    @PostMapping("/game/v1/lobby")
    public ResponseEntity<String> game_lobby(@RequestHeader("Authorization") String token, @RequestBody Map<String, Object> request) {
        String url = getNextServiceUrl("game_service") + "/game/v1/lobby";

        // Make the HTTP request and get the response
        return postWithAuth(url, token, request);
    }

    @GetMapping("/game/v1/lobby/{id}")
    public ResponseEntity<String> get_ws(@PathVariable String id) {
        String url = getNextServiceUrl("game_service") + "/game/v1/lobby/" + id;

        // Make the HTTP request and get the response
        return getStringResponseEntity(url);
    }


    @PostMapping("/user/v1/auth/register")
    public ResponseEntity<String> register(@RequestBody Map<String, String> request) {
        String url = getNextServiceUrl("auth_service") + "/user/v1/auth/register";
        return postRequest(url, request);
    }


    @PostMapping("/user/v1/auth/login")
    public ResponseEntity<String> login(@RequestBody Map<String, String> request) {
        String url = getNextServiceUrl("auth_service") + "/user/v1/auth/login";
        return postRequest(url, request);
    }

    @GetMapping("/user/v1/balance")
    public ResponseEntity<String> getBalance(@RequestHeader("Authorization") String token) {
        String url = getNextServiceUrl("auth_service") + "/user/v1/balance";
        return getWithAuth(url, token);
    }

    @GetMapping("/user/v1/auth/validate")
    public ResponseEntity<String> validate(@RequestHeader("Authorization") String token) {
        String url = getNextServiceUrl("auth_service") + "/user/v1/auth/validate";
        return getWithAuth(url, token);
    }

    @PostMapping("/user/v1/balance")
    public ResponseEntity<String> setBalance(@RequestHeader("Authorization") String token, @RequestBody Map<String, Object> request) {
        String url = getNextServiceUrl("auth_service") + "/user/v1/balance";
        return postWithAuth(url, token, request);
    }

    @PutMapping("/user/v1/balance")
    public ResponseEntity<String> updateBalance(@RequestHeader("Authorization") String token, @RequestBody Map<String, Object> request) {
        String url = getNextServiceUrl("auth_service") + "/user/v1/balance";
        return putWithAuth(url, token, request);
    }

    private ResponseEntity<String> postWithAuth(String url, String token, Map<String, Object> request) {
        HttpHeaders headers = new HttpHeaders();
        headers.add("Authorization", token); // Set the Authorization header with Bearer prefix
        headers.setContentType(MediaType.APPLICATION_JSON); // Set the content type to JSON

        return RetryUtils.retryRequest(() -> {
            HttpEntity<Map<String, Object>> entity = new HttpEntity<>(request, headers);
            return restTemplate.exchange(url, HttpMethod.POST, entity, String.class);
        }, url, 3);
    }

    private ResponseEntity<String> putWithAuth(String url, String token, Map<String, Object> request) {
        HttpHeaders headers = new HttpHeaders();
        headers.add("Authorization", token); // Set the Authorization header with Bearer prefix
        headers.setContentType(MediaType.APPLICATION_JSON); // Set the content type to JSON

        return RetryUtils.retryRequest(() -> {
            HttpEntity<Map<String, Object>> entity = new HttpEntity<>(request, headers);
            return restTemplate.exchange(url, HttpMethod.PUT, entity, String.class);
        }, url, 3);
    }

    private ResponseEntity<String> getWithAuth(String url, String token) {
        HttpHeaders headers = new HttpHeaders();
        headers.add("Authorization", token); // Set the Authorization header with Bearer prefix

        return RetryUtils.retryRequest(() -> {
            HttpEntity<Void> entity = new HttpEntity<>(headers);
            return restTemplate.exchange(url, HttpMethod.GET, entity, String.class);
        }, url, 3);
    }

    private ResponseEntity<String> postRequest(String url, Map<String, String> request) {
        return RetryUtils.retryRequest(() -> restTemplate.postForEntity(url, request, String.class), url, 3);
    }

    private ResponseEntity<String> getStringResponseEntity(String url) {
        return RetryUtils.retryRequest(() -> restTemplate.getForEntity(url, String.class), url, 3);
    }
}
