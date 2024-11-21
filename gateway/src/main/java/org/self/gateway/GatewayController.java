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
        List<String> urls = new ArrayList<>(services.get("auth_service"));
        String url = getNextServiceUrl("auth_service");
        urls.remove(url);

        url = url + "/user/v1/status";
        urls.replaceAll(s -> s + "/user/v1/status");

        // Make the HTTP request and get the response
        return getStringResponseEntity(url, urls);
    }

    @GetMapping("/game/v1/status")
    public ResponseEntity<String> game_status() {
        List<String> urls = new ArrayList<>(services.get("game_service"));
        String url = getNextServiceUrl("game_service");
        urls.remove(url);

        url = url + "/game/v1/status";
        urls.replaceAll(s -> s + "/game/v1/status");


        // Make the HTTP request and get the response
        return getStringResponseEntity(url, urls);
    }

    @PostMapping("/game/v1/lobby")
    public ResponseEntity<String> game_lobby(@RequestHeader("Authorization") String token, @RequestBody Map<String, Object> request) {
        List<String> urls = new ArrayList<>(services.get("game_service"));
        String url = getNextServiceUrl("game_service");
        urls.remove(url);

        url = url + "/game/v1/lobby";
        urls.replaceAll(s -> s + "/game/v1/lobby");

        // Make the HTTP request and get the response
        return postWithAuth(url, urls, token, request);
    }

    @GetMapping("/game/v1/lobby/{id}")
    public ResponseEntity<String> get_ws(@PathVariable String id) {
        List<String> urls = new ArrayList<>(services.get("game_service"));
        String url = getNextServiceUrl("game_service");
        urls.remove(url);

        url = url + "/game/v1/lobby/" + id;
        urls.replaceAll(s -> s + "/game/v1/lobby/" + id);

        // Make the HTTP request and get the response
        return getStringResponseEntity(url, urls);
    }


    @PostMapping("/user/v1/auth/register")
    public ResponseEntity<String> register(@RequestBody Map<String, String> request) {
        List<String> urls = new ArrayList<>(services.get("auth_service"));
        String url = getNextServiceUrl("auth_service");
        urls.remove(url);

        url = url + "/user/v1/auth/register";
        urls.replaceAll(s -> s + "/user/v1/auth/register");

        return postRequest(url, urls, request);
    }


    @PostMapping("/user/v1/auth/login")
    public ResponseEntity<String> login(@RequestBody Map<String, String> request) {
        List<String> urls = new ArrayList<>(services.get("auth_service"));
        String url = getNextServiceUrl("auth_service");
        urls.remove(url);

        url = url + "/user/v1/auth/login";
        urls.replaceAll(s -> s + "/user/v1/auth/login");

        return postRequest(url, urls, request);
    }

    @GetMapping("/user/v1/balance")
    public ResponseEntity<String> getBalance(@RequestHeader("Authorization") String token) {
        List<String> urls = new ArrayList<>(services.get("auth_service"));
        String url = getNextServiceUrl("auth_service");
        urls.remove(url);

        url = url + "/user/v1/balance";
        urls.replaceAll(s -> s + "/user/v1/balance");

        return getWithAuth(url, urls, token);
    }

    @GetMapping("/user/v1/auth/validate")
    public ResponseEntity<String> validate(@RequestHeader("Authorization") String token) {
        List<String> urls = new ArrayList<>(services.get("auth_service"));
        String url = getNextServiceUrl("auth_service");
        urls.remove(url);

        url = url + "/user/v1/auth/validate";
        urls.replaceAll(s -> s + "/user/v1/auth/validate");

        return getWithAuth(url, urls, token);
    }

    @PostMapping("/user/v1/balance")
    public ResponseEntity<String> setBalance(@RequestHeader("Authorization") String token, @RequestBody Map<String, Object> request) {
        List<String> urls = new ArrayList<>(services.get("auth_service"));
        String url = getNextServiceUrl("auth_service");
        urls.remove(url);

        url = url + "/user/v1/balance";
        urls.replaceAll(s -> s + "/user/v1/balance");
        return postWithAuth(url, urls, token, request);
    }

    @PutMapping("/user/v1/balance")
    public ResponseEntity<String> updateBalance(@RequestHeader("Authorization") String token, @RequestBody Map<String, Object> request) {
        List<String> urls = new ArrayList<>(services.get("auth_service"));
        String url = getNextServiceUrl("auth_service");
        urls.remove(url);

        url = url + "/user/v1/balance";
        urls.replaceAll(s -> s + "/user/v1/balance");

        return putWithAuth(url, urls, token, request);
    }

    private ResponseEntity<String> postWithAuth(String url, List<String> other_urls, String token, Map<String, Object> request) {
        HttpHeaders headers = new HttpHeaders();
        headers.add("Authorization", token); // Set the Authorization header with Bearer prefix
        headers.setContentType(MediaType.APPLICATION_JSON); // Set the content type to JSON

        List<String> allUrls = new ArrayList<>();
        allUrls.add(url);
        allUrls.addAll(other_urls);

        for (String serviceUrl : allUrls) {
            try {
                System.out.println("Trying service URL: " + serviceUrl);

                // Retry the request for the current URL
                ResponseEntity<String> response = RetryUtils.retryRequest(() -> {
                    HttpEntity<Map<String, Object>> entity = new HttpEntity<>(request, headers);
                    return restTemplate.exchange(serviceUrl, HttpMethod.POST, entity, String.class);
                }, serviceUrl, 3);
                // If the request is successful, return the response
                if (response.getStatusCode() != HttpStatus.REQUEST_TIMEOUT && response.getStatusCode() != HttpStatus.INTERNAL_SERVER_ERROR) {
                    return response;
                }
            } catch (Exception ignored) {
            }
        }

        System.out.println("All services failed:");
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body("All services are down:");
    }

    private ResponseEntity<String> putWithAuth(String url, List<String> other_urls, String token, Map<String, Object> request) {
        HttpHeaders headers = new HttpHeaders();
        headers.add("Authorization", token); // Set the Authorization header with Bearer prefix
        headers.setContentType(MediaType.APPLICATION_JSON); // Set the content type to JSON

        List<String> allUrls = new ArrayList<>();
        allUrls.add(url);
        allUrls.addAll(other_urls);

        for (String serviceUrl : allUrls) {
            try {
                System.out.println("Trying service URL: " + serviceUrl);

                // Retry the request for the current URL
                ResponseEntity<String> response = RetryUtils.retryRequest(() -> {
                    HttpEntity<Map<String, Object>> entity = new HttpEntity<>(request, headers);
                    return restTemplate.exchange(serviceUrl, HttpMethod.PUT, entity, String.class);
                }, serviceUrl, 3);
                // If the request is successful, return the response
                if (response.getStatusCode() != HttpStatus.REQUEST_TIMEOUT && response.getStatusCode() != HttpStatus.INTERNAL_SERVER_ERROR) {
                    return response;
                }
            } catch (Exception ignored) {
            }
        }

        System.out.println("All services failed:");
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body("All services are down:");
    }

    private ResponseEntity<String> getWithAuth(String url, List<String> other_urls, String token) {
        HttpHeaders headers = new HttpHeaders();
        headers.add("Authorization", token); // Set the Authorization header with Bearer prefix

        List<String> allUrls = new ArrayList<>();
        allUrls.add(url);
        allUrls.addAll(other_urls);
        for (String serviceUrl : allUrls) {
            try {
                System.out.println("Trying service URL: " + serviceUrl);

                // Retry the request for the current URL
                ResponseEntity<String> response = RetryUtils.retryRequest(() -> {
                    HttpEntity<Void> entity = new HttpEntity<>(headers);
                    return restTemplate.exchange(serviceUrl, HttpMethod.GET, entity, String.class);
                }, serviceUrl, 3);

                // If the request is successful, return the response
                if (response.getStatusCode() != HttpStatus.REQUEST_TIMEOUT && response.getStatusCode() != HttpStatus.INTERNAL_SERVER_ERROR) {
                    return response;
                }
            } catch (Exception ignored) {
            }
        }
        System.out.println("All services failed:");
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body("All services are down:");
    }

    private ResponseEntity<String> postRequest(String url, List<String> other_urls, Map<String, String> request) {
        List<String> allUrls = new ArrayList<>();
        allUrls.add(url);
        allUrls.addAll(other_urls);
        for (String serviceUrl : allUrls) {
            try {
                System.out.println("Trying service URL: " + serviceUrl);

                // Retry the request for the current URL
                ResponseEntity<String> response = RetryUtils.retryRequest(() -> restTemplate.postForEntity(serviceUrl, request, String.class), serviceUrl, 3);
                // If the request is successful, return the response
                if (response.getStatusCode() != HttpStatus.REQUEST_TIMEOUT && response.getStatusCode() != HttpStatus.INTERNAL_SERVER_ERROR) {
                    return response;
                }
            } catch (Exception ignored) {
            }
        }
        System.out.println("All services failed:");
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body("All services are down:");
    }

    private ResponseEntity<String> getStringResponseEntity(String url, List<String> other_urls) {
        List<String> allUrls = new ArrayList<>();
        allUrls.add(url);
        allUrls.addAll(other_urls);

        for (String serviceUrl : allUrls) {
            try {
                System.out.println("Trying service URL: " + serviceUrl);

                // Retry the request for the current URL
                ResponseEntity<String> response = RetryUtils.retryRequest(() -> restTemplate.getForEntity(serviceUrl, String.class), serviceUrl, 3);
                // If the request is successful, return the response
                if (response.getStatusCode() != HttpStatus.REQUEST_TIMEOUT && response.getStatusCode() != HttpStatus.INTERNAL_SERVER_ERROR) {
                    return response;
                }
            } catch (Exception ignored) {
            }
        }
        System.out.println("All services failed:");
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body("All services are down:");
    }
}