package com.finassist.backend.client;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;

@Component
public class PythonAiServiceClient {

    private final HttpClient httpClient;
    private final String baseUrl;

    public PythonAiServiceClient(@Value("${ai-service.base-url}") String baseUrl) {
        this.baseUrl = baseUrl;
        this.httpClient = HttpClient.newBuilder()
                .version(HttpClient.Version.HTTP_1_1)   // <-- the actual fix
                .connectTimeout(Duration.ofSeconds(5))
                .build();
    }

    public void triggerProcessing(Long documentId, String filePath, String fileType) {
        String json = "{\"documentId\":" + documentId
                + ",\"filePath\":" + jsonString(filePath)
                + ",\"fileType\":" + jsonString(fileType) + "}";

        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(baseUrl + "/internal/v1/process"))
                .header("Content-Type", "application/json")
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
                    Thread.sleep(1000L * attempt); // 1s, then 2s backoff
                } catch (InterruptedException ie) {
                    Thread.currentThread().interrupt();
                }
            } catch (Exception e) {
                throw new IllegalStateException("Failed to reach AI service: " + e.getMessage(), e);
            }
        }
    }

    private String jsonString(String value) {
        return "\"" + value.replace("\\", "\\\\").replace("\"", "\\\"") + "\"";
    }

    public record QueryResult(String answer, java.util.List<Citation> citations) {
        public record Citation(Long documentId, Integer page) {}
    }

    public QueryResult query(String question, java.util.List<Long> documentIds) {
        String idsJson = documentIds.stream().map(String::valueOf)
                .collect(java.util.stream.Collectors.joining(",", "[", "]"));
        String json = "{\"question\":" + jsonString(question) + ",\"documentIds\":" + idsJson + "}";

        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(baseUrl + "/internal/v1/query"))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(json))
                .timeout(Duration.ofSeconds(120))
                .build();

        try {
            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
            if (response.statusCode() >= 300) {
                throw new IllegalStateException("AI service returned " + response.statusCode() + ": " + response.body());
            }
            return parseQueryResult(response.body());
        } catch (Exception e) {
            throw new IllegalStateException("Failed to query AI service: " + e.getMessage(), e);
        }
    }

    private QueryResult parseQueryResult(String body) {
        // minimal hand-rolled parsing to avoid adding a JSON dependency
        String answer = extractJsonField(body, "answer");
        java.util.List<QueryResult.Citation> citations = new java.util.ArrayList<>();
        java.util.regex.Matcher m = java.util.regex.Pattern
                .compile("\"documentId\":(\\d+),\\s*\"page\":(\\d+)")
                .matcher(body);
        while (m.find()) {
            citations.add(new QueryResult.Citation(Long.parseLong(m.group(1)), Integer.parseInt(m.group(2))));
        }
        return new QueryResult(answer, citations);
    }

    private String extractJsonField(String body, String field) {
        java.util.regex.Matcher m = java.util.regex.Pattern
                .compile("\"" + field + "\":\"((?:[^\"\\\\]|\\\\.)*)\"")
                .matcher(body);
        if (m.find()) {
            return m.group(1).replace("\\n", "\n").replace("\\\"", "\"").replace("\\\\", "\\");
        }
        return "";
    }




}

