// swift-tools-version: 5.9
// The swift-tools-version declares the minimum version of Swift required to build this package.

import PackageDescription

let package = Package(
    name: "OncoRadApp",
    platforms: [
        .iOS(.v17),
        .macOS(.v14)
    ],
    products: [
        .library(
            name: "OncoRadApp",
            targets: ["OncoRadApp"]),
    ],
    targets: [
        .target(
            name: "OncoRadApp",
            path: "OncoRadApp"),
        .testTarget(
            name: "OncoRadAppTests",
            dependencies: ["OncoRadApp"]),
    ]
)
