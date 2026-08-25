package com.finassist.backend.client;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.List;

@Component
public class PythonAiServiceClient {

    private final HttpClient httpClient;
    private final ObjectMapper objectMapper;
    private final String baseUrl;
    private final String internalToken;

    public PythonAiServiceClient(@Value("${ai-service.base-url}") String baseUrl,
                                 @Value("${internal.service-token}") String internalToken,
                                 ObjectMapper objectMapper) {
        this.baseUrl = baseUrl;
        this.internalToken = internalToken;
        this.objectMapper = objectMapper;
        this.httpClient = HttpClient.newBuilder()
                .version(HttpClient.Version.HTTP_1_1)
                .connectTimeout(Duration.ofSeconds(5))
                .build();
    }

    public record ProcessRequest(Long documentId, String filePath, String fileType) {}
    public record QueryRequest(String question, List<Long> documentIds) {}

    @JsonIgnoreProperties(ignoreUnknown = true)
    public record QueryResult(String answer, List<Citation> citations) {
        @JsonIgnoreProperties(ignoreUnknown = true)
        public record Citation(Long documentId, Integer page) {}
    }

    public void triggerProcessing(Long documentId, String filePath, String fileType) {
        try {
            String json = objectMapper.writeValueAsString(new ProcessRequest(documentId, filePath, fileType));

            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(baseUrl + "/internal/v1/process"))
                    .header("Content-Type", "application/json")
                    .header("X-Internal-Token", internalToken)
                    .POST(HttpRequest.BodyPublishers.ofString(json))
                    .build();

            int maxAttempts = 3;
            for (int attempt = 1; attempt <= maxAttempts; attempt++) {
                try {
                    HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
                    if (response.statusCode() >= 300) {
                        throw new IllegalStateException("AI service returned " + response.statusCode() + ": " + response.body());
                    }
                    return; // success
                } catch (java.net.ConnectException e) {
                    if (attempt == maxAttempts) {
                        throw new IllegalStateException("AI service unreachable after " + maxAttempts + " attempts", e);
                    }
                    try {
                        Thread.sleep(1000L * attempt);
                    } catch (InterruptedException ie) {
                        Thread.currentThread().interrupt();
                    }
                }
            }
        } catch (Exception e) {
            throw new IllegalStateException("Failed to trigger AI service processing: " + e.getMessage(), e);
        }
    }

    public void deleteDocumentVectors(Long documentId) {
        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(baseUrl + "/internal/v1/documents/" + documentId))
                .header("X-Internal-Token", internalToken)
                .DELETE()
                .build();
        try {
            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
            if (response.statusCode() >= 300 && response.statusCode() != 404) {
                throw new IllegalStateException("AI service failed vector cleanup: " + response.body());
            }
        } catch (Exception e) {
            System.err.println("Warning: failed to delete vectors from AI service: " + e.getMessage());
        }
    }

    public QueryResult query(String question, List<Long> documentIds) {
        try {
            String json = objectMapper.writeValueAsString(new QueryRequest(question, documentIds != null ? documentIds : List.of()));

            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(baseUrl + "/internal/v1/query"))
                    .header("Content-Type", "application/json")
                    .header("X-Internal-Token", internalToken)
                    .POST(HttpRequest.BodyPublishers.ofString(json))
                    .timeout(Duration.ofSeconds(120))
                    .build();

            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
            if (response.statusCode() >= 300) {
                throw new IllegalStateException("AI service returned " + response.statusCode() + ": " + response.body());
            }
            QueryResult result = objectMapper.readValue(response.body(), QueryResult.class);
            return result != null ? result : new QueryResult("", List.of());
        } catch (Exception e) {
            throw new IllegalStateException("Failed to query AI service: " + e.getMessage(), e);
        }
    }
}
