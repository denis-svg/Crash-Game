package org.self.gateway;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.RestClientException;

import java.util.function.Supplier;

public class RetryUtils {

    public static ResponseEntity<String> retryRequest(Supplier<ResponseEntity<String>> request, String url, int maxRetries) {
        int retryCount = 0;

        while (retryCount < maxRetries) {
            try {
                // Attempt to execute the request
                return request.get(); // Success, return the response

            } catch (HttpClientErrorException e) {
                HttpStatus statusCode = (HttpStatus) e.getStatusCode();

                // Retry only for server-side errors (5xx)
                if (isRetryableStatusCode(statusCode)) {
                    retryCount++;
                    if (retryCount >= maxRetries) {
                        System.out.println("Request failed after " + maxRetries + " retries for URL: " + url + ". Final status code: " + statusCode);
                        return ResponseEntity.status(e.getStatusCode()).body(e.getResponseBodyAsString());
                    }
                } else {
                    // For client-side errors (4xx), don't retry
                    System.out.println("Client-side error occurred for URL: " + url + ". Status code: " + statusCode);
                    return ResponseEntity.status(statusCode).body(e.getResponseBodyAsString());
                }

            } catch (RestClientException e) {
                // Retry for timeouts or general connection errors
                retryCount++;
                if (retryCount >= maxRetries) {
                    System.out.println("Request failed after " + maxRetries + " retries for URL: " + url + ". Request timed out or connection error.");
                    return ResponseEntity.status(HttpStatus.REQUEST_TIMEOUT).body("An error occurred during the request");
                }
            } catch (Exception e) {
                // Catch-all for any other exceptions (optional retries for unknown errors)
                retryCount++;
                if (retryCount >= maxRetries) {
                    System.out.println("Request failed after " + maxRetries + " retries for URL: " + url + ". An unknown error occurred.");
                    return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body("An error occurred while processing the request");
                }
            }
        }

        // If all retries failed
        System.out.println("All retries failed for URL: " + url);
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body("All retry attempts failed");
    }

    // Helper method to check if the status code is retryable
    private static boolean isRetryableStatusCode(HttpStatus statusCode) {
        return statusCode.is5xxServerError() || statusCode == HttpStatus.REQUEST_TIMEOUT;
    }
}