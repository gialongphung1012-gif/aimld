import SwiftUI

struct LicenseView: View {
    @ObservedObject var model: LicenseViewModel
    @State private var key = ""
    var body: some View {
        ZStack {
            LinearGradient(colors: [Color(red: 0.04, green: 0.08, blue: 0.16), .black], startPoint: .topLeading, endPoint: .bottomTrailing).ignoresSafeArea()
            VStack(alignment: .leading, spacing: 22) {
                HStack(spacing: 12) {
                    Text("A").font(.system(size: 28, weight: .black, design: .rounded)).foregroundStyle(.black).frame(width: 52, height: 52).background(Color.cyan.gradient, in: RoundedRectangle(cornerRadius: 16))
                    VStack(alignment: .leading, spacing: 3) { Text("AIMLD").font(.system(size: 25, weight: .bold, design: .rounded)); Text("LICENSE VERIFICATION").font(.caption2.weight(.bold)).tracking(2).foregroundStyle(.cyan) }
                }.padding(.top, 24)
                VStack(alignment: .leading, spacing: 8) { Text("Xác minh bản quyền").font(.title2.bold()); Text("Nhập key để kích hoạt giấy phép trên thiết bị này.").foregroundStyle(.white.opacity(0.65)).font(.subheadline) }
                TextField("AIMLD-XXXXX-XXXXX-XXXXX-XXXXX", text: $key).textInputAutocapitalization(.characters).autocorrectionDisabled().font(.system(.body, design: .monospaced)).padding(15).background(.white.opacity(0.06), in: RoundedRectangle(cornerRadius: 13)).overlay(RoundedRectangle(cornerRadius: 13).stroke(.white.opacity(0.12)))
                Button { Task { await model.activate(key: key) } } label: {
                    HStack { if model.isBusy { ProgressView().tint(.black) }; Text(model.isBusy ? "Đang xác minh…" : "Xác minh key").fontWeight(.bold); Spacer(); Image(systemName: "arrow.right") }
                        .foregroundStyle(.black).padding(16).background(Color.cyan.gradient, in: RoundedRectangle(cornerRadius: 13))
                }.disabled(model.isBusy || key.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                Button("Kiểm tra phiên đã kích hoạt") {
                    Task { await model.validateSavedActivation() }
                }
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(.cyan)
                .disabled(model.isBusy)
                if let message = model.message {
                    VStack(alignment: .leading, spacing: 8) {
                        Label(model.isLicensed ? "Bản quyền hợp lệ" : "Trạng thái bản quyền", systemImage: model.isLicensed ? "checkmark.seal.fill" : "info.circle.fill").font(.headline).foregroundStyle(model.isLicensed ? .green : .orange)
                        Text(message).font(.subheadline).foregroundStyle(.white.opacity(0.8))
                        if let expiry = model.expiresAt { Text("Hết hạn: \(expiry.formatted(date: .long, time: .shortened))").font(.caption).foregroundStyle(.white.opacity(0.6)) }
                    }.padding(16).frame(maxWidth: .infinity, alignment: .leading).background(.white.opacity(0.06), in: RoundedRectangle(cornerRadius: 14))
                }
                Spacer(minLength: 8)
                Text("Xác minh trực tuyến · Không lưu mật khẩu quản trị trên thiết bị").font(.caption2).foregroundStyle(.white.opacity(0.45)).frame(maxWidth: .infinity)
            }.padding(22)
        }.preferredColorScheme(.dark)
    }
}
