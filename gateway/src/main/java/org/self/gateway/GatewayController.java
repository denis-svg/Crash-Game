package org.self.gateway;

import org.springframework.http.*;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.RestTemplate;

import java.util.Map;

@RestController
@RequestMapping("/gateway")
public class GatewayController {

    private final RestTemplate restTemplate;

    public GatewayController() {
        this.restTemplate = this.createRestTemplate();
    }

    private RestTemplate createRestTemplate() {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(500); // Set connect timeout (in milliseconds)
        factory.setReadTimeout(5000); // Set read timeout (in milliseconds)
        return new RestTemplate(factory);
    }

    @GetMapping("/user/v1/status")
    public ResponseEntity<String> user_status() {
        String url = "http://0.0.0.0:5001/user/v1/status";

        // Make the HTTP request and get the response
        return getStringResponseEntity(url);
    }

    @GetMapping("/game/v1/status")
    public ResponseEntity<String> game_status() {
        String url = "http://0.0.0.0:5003/game/v1/status";

        // Make the HTTP request and get the response
        return getStringResponseEntity(url);
    }

    @PostMapping("/game/v1/lobby")
    public ResponseEntity<String> game_lobby(@RequestHeader("Authorization") String token, @RequestBody Map<String, Object> request) {
        String url = "http://0.0.0.0:5003/game/v1/lobby";

        // Make the HTTP request and get the response
        return postWithAuth(url, token, request);
    }

    @PostMapping("/user/v1/auth/register")
    public ResponseEntity<String> register(@RequestBody Map<String, String> request) {
        String url = "http://0.0.0.0:5000/user/v1/auth/register";
        return postRequest(url, request);
    }


    @PostMapping("/user/v1/auth/login")
    public ResponseEntity<String> login(@RequestBody Map<String, String> request) {
        String url = "http://0.0.0.0:5000/user/v1/auth/login";
        return postRequest(url, request);
    }

    @GetMapping("/user/v1/balance")
    public ResponseEntity<String> getBalance(@RequestHeader("Authorization") String token) {
        String url = "http://0.0.0.0:5000/user/v1/balance";
        return getWithAuth(url, token);
    }

    @GetMapping("/user/v1/auth/validate")
    public ResponseEntity<String> validate(@RequestHeader("Authorization") String token) {
        String url = "http://0.0.0.0:5000/user/v1/auth/validate";
        return getWithAuth(url, token);
    }

    @PostMapping("/user/v1/balance")
    public ResponseEntity<String> setBalance(@RequestHeader("Authorization") String token, @RequestBody Map<String, Object> request) {
        String url = "http://0.0.0.0:5000/user/v1/balance";
        return postWithAuth(url, token, request);
    }

    @PutMapping("/user/v1/balance")
    public ResponseEntity<String> updateBalance(@RequestHeader("Authorization") String token, @RequestBody Map<String, Object> request) {
        String url = "http://0.0.0.0:5000/user/v1/balance";
        return putWithAuth(url, token, request);
    }

    private ResponseEntity<String> postWithAuth(String url, String token, Map<String, Object> request) {
        HttpHeaders headers = new HttpHeaders();
        headers.add("Authorization", token); // Set the Authorization header with Bearer prefix
        headers.setContentType(MediaType.APPLICATION_JSON); // Set the content type to JSON

        try {
            // Create an HttpEntity with the headers and body
            ResponseEntity<String> responseEntity = restTemplate.exchange(url, HttpMethod.POST, new HttpEntity<>(request, headers), String.class);
            return ResponseEntity.ok(responseEntity.getBody());
        } catch (HttpClientErrorException e) {
            return ResponseEntity.status(e.getStatusCode()).body(e.getResponseBodyAsString());
        } catch (Exception e) {
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body("An error occurred while processing the request");
        }
    }

    private ResponseEntity<String> putWithAuth(String url, String token, Map<String, Object> request) {
        HttpHeaders headers = new HttpHeaders();
        headers.add("Authorization", token); // Set the Authorization header with Bearer prefix
        headers.setContentType(MediaType.APPLICATION_JSON); // Set the content type to JSON

        try {
            // Create an HttpEntity with the headers and body
            ResponseEntity<String> responseEntity = restTemplate.exchange(url, HttpMethod.PUT, new HttpEntity<>(request, headers), String.class);
            return ResponseEntity.ok(responseEntity.getBody());
        } catch (HttpClientErrorException e) {
            return ResponseEntity.status(e.getStatusCode()).body(e.getResponseBodyAsString());
        } catch (Exception e) {
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body("An error occurred while processing the request");
        }
    }

    private ResponseEntity<String> getWithAuth(String url, String token) {
        HttpHeaders headers = new HttpHeaders();
        headers.add("Authorization", token); // Set the Authorization header with Bearer prefix

        try {
            // Create an HttpEntity with the headers
            ResponseEntity<String> responseEntity = restTemplate.exchange(url, HttpMethod.GET, new HttpEntity<>(headers), String.class);
            return ResponseEntity.ok(responseEntity.getBody());
        } catch (HttpClientErrorException e) {
            return ResponseEntity.status(e.getStatusCode()).body(e.getResponseBodyAsString());
        } catch (Exception e) {
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body("An error occurred while fetching balance");
        }
    }

    private ResponseEntity<String> postRequest(String url, Map<String, String> request) {
        try{
            ResponseEntity<String> responseEntity = restTemplate.postForEntity(url, request, String.class);
            return ResponseEntity.ok(responseEntity.getBody());
        }catch (HttpClientErrorException e){
            return ResponseEntity.status(e.getStatusCode()).body(e.getResponseBodyAsString());
        }
    }

    private ResponseEntity<String> getStringResponseEntity(String url) {
        try {
            ResponseEntity<String> responseEntity = restTemplate.getForEntity(url, String.class);

            // Check the status code and return accordingly
            if (responseEntity.getStatusCode() == HttpStatus.OK) {
                // Return 200 OK and the response body from the user service
                return ResponseEntity.ok(responseEntity.getBody());
            }
        }
        catch (Exception e) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND).body("Service not found");
        }
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body("An error occurred");
    }
}
