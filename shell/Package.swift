// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "AppleLocalOrganizerShell",
    platforms: [
        .macOS(.v15),
    ],
    products: [
        .executable(name: "AppleLocalOrganizerApp", targets: ["AppleLocalOrganizerApp"]),
    ],
    targets: [
        .executableTarget(
            name: "AppleLocalOrganizerApp",
            resources: [
                .process("Resources"),
            ]
        ),
        .testTarget(
            name: "AppleLocalOrganizerAppTests",
            dependencies: ["AppleLocalOrganizerApp"]
        ),
    ]
)
