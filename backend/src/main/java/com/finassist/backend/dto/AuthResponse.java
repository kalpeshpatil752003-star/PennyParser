package com.finassist.backend.dto;

public class AuthResponse {
    private String accessToken;
    private String email;
    private String fullName;

    public AuthResponse(String accessToken, String email, String fullName) {
        this.accessToken = accessToken;
        this.email = email;
        this.fullName = fullName;
    }
    public String getAccessToken() { return accessToken; }
    public String getEmail() { return email; }
    public String getFullName() { return fullName; }
}