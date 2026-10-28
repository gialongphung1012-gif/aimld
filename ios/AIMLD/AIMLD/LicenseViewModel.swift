import Foundation
import Security
import SwiftUI
import UIKit

@MainActor final class LicenseViewModel: ObservableObject {
    @Published var isBusy = false
    @Published var message: String?
    @Published var isLicensed = false
    @Published var expiresAt: Date?

    // Set this to your deployed HTTPS API origin, e.g. https://licenses.example.com
    private let baseURL = URL(string: "https://YOUR-DOMAIN.example")!
    private let deviceID = KeychainStore.deviceID()
    private let tokenKey = "aimld.activation.token"

    func activate(key: String) async {
        guard baseURL.host != "YOUR-DOMAIN.example", baseURL.scheme == "https" else {
            message = "Hãy cấu hình baseURL thành domain HTTPS của AIMLD trước khi build."
            isLicensed = false; return
        }
        isBusy = true; defer { isBusy = false }
        do {
            let response: LicenseResponse = try await request(path: "/api/license/activate", body: ["key": key.trimmingCharacters(in: .whitespacesAndNewlines), "device_id": deviceID, "device_label": UIDeviceLabel.current])
            if let token = response.activationToken { KeychainStore.save(token, for: tokenKey) }
            update(response)
        } catch { message = error.localizedDescription; isLicensed = false }
    }

    func validateSavedActivation() async {
        guard let token = KeychainStore.load(tokenKey) else {
            message = "Thiết bị chưa có phiên kích hoạt. Hãy nhập key để kích hoạt."
            isLicensed = false
            return
        }
        isBusy = true; defer { isBusy = false }
        do {
            let response: LicenseResponse = try await request(
                path: "/api/license/validate",
                body: ["activation_token": token, "device_id": deviceID]
            )
            update(response)
        } catch { message = error.localizedDescription; isLicensed = false }
    }

    func signOut() {
        let token = KeychainStore.load(tokenKey)
        KeychainStore.delete(tokenKey)
        isLicensed = false; expiresAt = nil; message = nil
        guard let token else { return }
        Task { _ = try? await request(path: "/api/license/deactivate", body: ["device_id": deviceID, "activation_token": token]) as LicenseResponse }
    }

    private func update(_ response: LicenseResponse) {
        isLicensed = response.ok && response.code == "KEY_VALID"
        message = response.message
        expiresAt = response.expiresAt.flatMap { ISO8601DateFormatter().date(from: $0) }
    }

    private func request<T: Decodable>(path: String, body: [String: String]) async throws -> T {
        let url = baseURL.appendingPathComponent(String(path.dropFirst()))
        var req = URLRequest(url: url); req.httpMethod = "POST"; req.timeoutInterval = 15
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = try JSONSerialization.data(withJSONObject: body)
        let (data, response) = try await URLSession.shared.data(for: req)
        guard let http = response as? HTTPURLResponse else { throw LicenseError.badResponse }
        let decoded = try JSONDecoder().decode(T.self, from: data)
        if !(200..<300).contains(http.statusCode), let error = decoded as? LicenseResponse {
            throw LicenseError.server(error.message ?? error.code ?? "Yêu cầu thất bại")
        }
        return decoded
    }
}

private struct LicenseResponse: Decodable {
    let ok: Bool
    let code: String?
    let message: String?
    let expiresAt: String?
    let activationToken: String?
    enum CodingKeys: String, CodingKey { case ok, code, message; case expiresAt = "expires_at"; case activationToken = "activation_token" }
}
private enum LicenseError: LocalizedError {
    case badResponse, server(String)
    var errorDescription: String? { switch self { case .badResponse: return "Phản hồi máy chủ không hợp lệ."; case .server(let s): return s } }
}
private enum UIDeviceLabel { static var current: String { "iOS device" } }
private enum KeychainStore {
    static func deviceID() -> String {
        if let existing = load("aimld.device.id") { return existing }
        let value = UUID().uuidString
        save(value, for: "aimld.device.id")
        return load("aimld.device.id") ?? value
    }
    static func save(_ value: String, for key: String) {
        let data = Data(value.utf8)
        let query: [String: Any] = [kSecClass as String: kSecClassGenericPassword, kSecAttrAccount as String: key, kSecValueData as String: data]
        SecItemDelete(query as CFDictionary); SecItemAdd(query as CFDictionary, nil)
    }
    static func delete(_ key: String) {
        SecItemDelete([kSecClass as String: kSecClassGenericPassword, kSecAttrAccount as String: key] as CFDictionary)
    }
    static func load(_ key: String) -> String? {
        let query: [String: Any] = [kSecClass as String: kSecClassGenericPassword, kSecAttrAccount as String: key, kSecReturnData as String: true, kSecMatchLimit as String: kSecMatchLimitOne]
        var item: CFTypeRef?; guard SecItemCopyMatching(query as CFDictionary, &item) == errSecSuccess, let data = item as? Data else { return nil }
        return String(data: data, encoding: .utf8)
    }
}
