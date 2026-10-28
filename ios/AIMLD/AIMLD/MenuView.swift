import SwiftUI

/// Giao diện menu mô phỏng: các công tắc chỉ thay đổi trạng thái hiển thị,
/// KHÔNG tác động tới game hay ứng dụng khác.
struct MenuView: View {
    @ObservedObject var model: LicenseViewModel

    @State private var tab = 0
    @State private var toggles: [String: Bool] = [:]
    @State private var sliders: [String: Double] = ["Giá trị 1": 50, "Giá trị 2": 30]

    private let sections: [(title: String, icon: String, items: [String])] = [
        ("Chính", "bolt.fill", ["Tính năng 1", "Tính năng 2", "Tính năng 3", "Tính năng 4"]),
        ("Hiển thị", "eye.fill", ["Hiển thị A", "Hiển thị B", "Hiển thị C", "Hiển thị D"]),
        ("Khác", "slider.horizontal.3", ["Tùy chọn 1", "Tùy chọn 2", "Tùy chọn 3"])
    ]

    var body: some View {
        ZStack {
            LinearGradient(colors: [Color(red: 0.04, green: 0.08, blue: 0.16), .black], startPoint: .topLeading, endPoint: .bottomTrailing).ignoresSafeArea()
            VStack(spacing: 16) {
                header
                tabBar
                ScrollView {
                    VStack(spacing: 10) {
                        ForEach(sections[tab].items, id: \.self) { name in
                            toggleRow(name)
                        }
                        if tab == 2 {
                            ForEach(Array(sliders.keys.sorted()), id: \.self) { name in
                                sliderRow(name)
                            }
                        }
                    }
                }
                Button(role: .destructive) { model.signOut() } label: {
                    Label("Đăng xuất", systemImage: "rectangle.portrait.and.arrow.right")
                        .frame(maxWidth: .infinity).padding(14)
                        .background(.white.opacity(0.06), in: RoundedRectangle(cornerRadius: 13))
                }
                Text("Giao diện mô phỏng · công tắc không có chức năng thật")
                    .font(.caption2).foregroundStyle(.white.opacity(0.45))
            }.padding(20)
        }.preferredColorScheme(.dark)
    }

    private var header: some View {
        HStack(spacing: 12) {
            Text("A").font(.system(size: 24, weight: .black, design: .rounded)).foregroundStyle(.black)
                .frame(width: 44, height: 44).background(Color.cyan.gradient, in: RoundedRectangle(cornerRadius: 13))
            VStack(alignment: .leading, spacing: 2) {
                Text("AIMLD MENU").font(.headline.bold())
                if let expiry = model.expiresAt {
                    Text("Hết hạn: \(expiry.formatted(date: .abbreviated, time: .shortened))")
                        .font(.caption).foregroundStyle(.white.opacity(0.6))
                }
            }
            Spacer()
            Image(systemName: "checkmark.seal.fill").foregroundStyle(.green)
        }
    }

    private var tabBar: some View {
        HStack(spacing: 8) {
            ForEach(sections.indices, id: \.self) { i in
                Button { tab = i } label: {
                    Label(sections[i].title, systemImage: sections[i].icon)
                        .font(.footnote.weight(.semibold)).frame(maxWidth: .infinity).padding(.vertical, 10)
                        .foregroundStyle(tab == i ? .black : .white)
                        .background(tab == i ? AnyShapeStyle(Color.cyan.gradient) : AnyShapeStyle(.white.opacity(0.06)), in: RoundedRectangle(cornerRadius: 11))
                }
            }
        }
    }

    private func toggleRow(_ name: String) -> some View {
        Toggle(name, isOn: Binding(get: { toggles[name] ?? false }, set: { toggles[name] = $0 }))
            .tint(.cyan).padding(14)
            .background(.white.opacity(0.06), in: RoundedRectangle(cornerRadius: 13))
    }

    private func sliderRow(_ name: String) -> some View {
        VStack(alignment: .leading) {
            HStack { Text(name); Spacer(); Text("\(Int(sliders[name] ?? 0))").foregroundStyle(.cyan) }
            Slider(value: Binding(get: { sliders[name] ?? 0 }, set: { sliders[name] = $0 }), in: 0...100).tint(.cyan)
        }.padding(14).background(.white.opacity(0.06), in: RoundedRectangle(cornerRadius: 13))
    }
}
