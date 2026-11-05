import Foundation
import AVFoundation
import CoreImage
import Vision

// Raw-frame mode avoids AVAssetReader/VTDecoderXPCService. Each frame gets its
// own autorelease pool and at most three encoder pixel buffers are in flight.
func rawMode() throws {
    let args = CommandLine.arguments
    guard args.count >= 7, let width = Int(args[2]), let height = Int(args[3]),
          width > 0, height > 0, width <= 1920, height <= 1920 else {
        throw NSError(domain: "Video", code: 1, userInfo: [NSLocalizedDescriptionKey: "Invalid raw frame dimensions"])
    }
    let preview = args[1] == "--raw-preview"
    let duration = Double(args[4]) ?? 0
    let destination = URL(fileURLWithPath: args[5])
    let radius = Double(args[6]) ?? 25
    let context = CIContext(options: [.useSoftwareRenderer: false, .cacheIntermediates: false])
    let colorSpace = CGColorSpaceCreateDeviceRGB()
    let request = VNGeneratePersonSegmentationRequest()
    request.qualityLevel = args.count > 7 && args[7] == "fast" ? .fast : .balanced
    request.outputPixelFormat = kCVPixelFormatType_OneComponent8
    // Avoid repeated Neural Engine compilation during consecutive exports.
    request.usesCPUOnly = true
    var writer: AVAssetWriter?
    var writerInput: AVAssetWriterInput?
    var adaptor: AVAssetWriterInputPixelBufferAdaptor?
    if !preview {
        let output = try AVAssetWriter(outputURL: destination, fileType: .mp4)
        let input = AVAssetWriterInput(mediaType: .video, outputSettings: [
            AVVideoCodecKey: AVVideoCodecType.h264, AVVideoWidthKey: width, AVVideoHeightKey: height,
            AVVideoCompressionPropertiesKey: [AVVideoAverageBitRateKey: 4500000, AVVideoAllowFrameReorderingKey: false]
        ])
        input.expectsMediaDataInRealTime = false
        let adapter = AVAssetWriterInputPixelBufferAdaptor(assetWriterInput: input, sourcePixelBufferAttributes: [
            kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA,
            kCVPixelBufferWidthKey as String: width, kCVPixelBufferHeightKey as String: height,
            kCVPixelBufferIOSurfacePropertiesKey as String: [:]
        ])
        output.add(input)
        guard output.startWriting() else { throw output.error! }
        output.startSession(atSourceTime: .zero)
        writer = output; writerInput = input; adaptor = adapter
    }
    defer { context.clearCaches() }
    let frameBytes = width * height * 4
    var frameIndex: Int64 = 0
    while true {
        let processed = try autoreleasepool { () throws -> Bool in
            var data = Data()
            data.reserveCapacity(frameBytes)
            while data.count < frameBytes {
                guard let chunk = try FileHandle.standardInput.read(upToCount: frameBytes - data.count), !chunk.isEmpty else {
                    if data.isEmpty { return false }
                    throw NSError(domain: "Video", code: 2, userInfo: [NSLocalizedDescriptionKey: "Truncated raw frame"])
                }
                data.append(chunk)
            }
            let image = CIImage(bitmapData: data, bytesPerRow: width * 4, size: CGSize(width: width, height: height), format: .BGRA8, colorSpace: colorSpace)
            let handler = VNImageRequestHandler(ciImage: image, options: [:])
            try handler.perform([request])
            var result = image
            if let mask = request.results?.first?.pixelBuffer {
                let base = CIImage(cvPixelBuffer: mask)
                let scaled = base.transformed(by: CGAffineTransform(scaleX: image.extent.width / base.extent.width, y: image.extent.height / base.extent.height))
                let blurred = image.clampedToExtent().applyingFilter("CIGaussianBlur", parameters: ["inputRadius": radius]).cropped(to: image.extent)
                result = image.applyingFilter("CIBlendWithMask", parameters: ["inputBackgroundImage": blurred, "inputMaskImage": scaled])
            }
            if preview {
                try context.writeJPEGRepresentation(of: result, to: destination, colorSpace: colorSpace, options: [:])
            } else if let output = writer, let input = writerInput, let adapter = adaptor {
                while !input.isReadyForMoreMediaData {
                    if output.status != .writing { throw output.error ?? NSError(domain: "Video", code: 3) }
                    Thread.sleep(forTimeInterval: 0.005)
                }
                guard let pool = adapter.pixelBufferPool else { throw NSError(domain: "Video", code: 4) }
                var buffer: CVPixelBuffer?
                let aux = [kCVPixelBufferPoolAllocationThresholdKey as String: 3] as CFDictionary
                var status = CVPixelBufferPoolCreatePixelBufferWithAuxAttributes(kCFAllocatorDefault, pool, aux, &buffer)
                while status == kCVReturnWouldExceedAllocationThreshold {
                    if output.status != .writing { throw output.error ?? NSError(domain: "Video", code: 5) }
                    Thread.sleep(forTimeInterval: 0.005)
                    status = CVPixelBufferPoolCreatePixelBufferWithAuxAttributes(kCFAllocatorDefault, pool, aux, &buffer)
                }
                guard status == kCVReturnSuccess, let target = buffer else { throw NSError(domain: "Video", code: 6) }
                context.render(result, to: target, bounds: image.extent, colorSpace: colorSpace)
                guard adapter.append(target, withPresentationTime: CMTime(value: frameIndex, timescale: 30)) else {
                    throw output.error ?? NSError(domain: "Video", code: 7)
                }
            }
            return true
        }
        if !processed { break }
        frameIndex += 1
        if frameIndex % 15 == 0 || preview {
            let percent = duration > 0 ? min(99, Double(frameIndex) / 30 / duration * 100) : 0
            print(String(format: "PROGRESS: %.1f%%", percent)); fflush(stdout)
            context.clearCaches()
        }
        if preview { break }
    }
    guard frameIndex > 0 else { throw NSError(domain: "Video", code: 8) }
    if let output = writer, let input = writerInput {
        input.markAsFinished()
        output.endSession(atSourceTime: CMTime(value: frameIndex, timescale: 30))
        let done = DispatchSemaphore(value: 0)
        output.finishWriting { done.signal() }
        done.wait()
        guard output.status == .completed else { throw output.error ?? NSError(domain: "Video", code: 9) }
    }
    print("PROGRESS: 100.0%"); fflush(stdout)
}

if CommandLine.arguments.count > 1 && ["--raw", "--raw-preview"].contains(CommandLine.arguments[1]) {
    do { try rawMode(); exit(0) }
    catch { fputs("Bokeh failed: \(error.localizedDescription)\n", stderr); exit(1) }
}

// Check for single-frame preview mode:
// Usage 1: cinematic_blur --preview <input_path> <output_jpg> [blur_radius]
// Usage 2: cinematic_blur <input_path> <output_mp4> [blur_radius] [quality]

guard CommandLine.arguments.count >= 3 else {
    fputs("Usage: cinematic_blur <input_path> <output_path> [blur_radius] [quality]\n", stderr)
    fputs("   or: cinematic_blur --preview <input_path> <output_jpg> [blur_radius]\n", stderr)
    exit(1)
}

if CommandLine.arguments[1] == "--preview" {
    guard CommandLine.arguments.count >= 4 else { exit(1) }
    let inPath = CommandLine.arguments[2]
    let outJpg = CommandLine.arguments[3]
    let blurRad: Double = CommandLine.arguments.count > 4 ? (Double(CommandLine.arguments[4]) ?? 22.0) : 22.0
    
    let inURL = URL(fileURLWithPath: inPath)
    let asset = AVURLAsset(url: inURL)
    guard let track = asset.tracks(withMediaType: .video).first else { exit(1) }
    
    let reader = try! AVAssetReader(asset: asset)
    let trackOut = AVAssetReaderTrackOutput(track: track, outputSettings: [kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA])
    reader.add(trackOut)
    reader.startReading()
    
    // Grab first valid frame around 1.0s or frame 15
    var sample: CMSampleBuffer?
    for _ in 0..<15 {
        if let s = trackOut.copyNextSampleBuffer() { sample = s } else { break }
    }
    reader.cancelReading()
    
    guard let s = sample, let imgBuf = CMSampleBufferGetImageBuffer(s) else { exit(1) }
    let origCI = CIImage(cvImageBuffer: imgBuf)
    
    let ciContext = CIContext(options: [.useSoftwareRenderer: false])
    let segReq = VNGeneratePersonSegmentationRequest()
    segReq.qualityLevel = .balanced
    let handler = VNImageRequestHandler(ciImage: origCI, options: [:])
    try? handler.perform([segReq])
    
    if let maskBuf = segReq.results?.first?.pixelBuffer {
        let rawMask = CIImage(cvPixelBuffer: maskBuf)
        let sx = origCI.extent.width / rawMask.extent.width
        let sy = origCI.extent.height / rawMask.extent.height
        let mask = rawMask.transformed(by: CGAffineTransform(scaleX: sx, y: sy))
        let blurred = origCI.clampedToExtent().applyingFilter("CIGaussianBlur", parameters: ["inputRadius": blurRad]).cropped(to: origCI.extent)
        let blended = origCI.applyingFilter("CIBlendWithMask", parameters: ["inputBackgroundImage": blurred, "inputMaskImage": mask])
        try? ciContext.writeJPEGRepresentation(of: blended, to: URL(fileURLWithPath: outJpg), colorSpace: CGColorSpaceCreateDeviceRGB(), options: [:])
    }
    print("PREVIEW_GENERATED"); fflush(stdout)
    exit(0)
}

// FULL VIDEO PROCESSING MODE
let inputPath = CommandLine.arguments[1]
let outputPath = CommandLine.arguments[2]
let blurRadius: Double = CommandLine.arguments.count > 3 ? (Double(CommandLine.arguments[3]) ?? 22.0) : 22.0
let qualityArg = CommandLine.arguments.count > 4 ? CommandLine.arguments[4].lowercased() : "balanced"

let inputURL = URL(fileURLWithPath: inputPath)
let outputURL = URL(fileURLWithPath: outputPath)

if FileManager.default.fileExists(atPath: outputPath) {
    try? FileManager.default.removeItem(at: outputURL)
}

let asset = AVURLAsset(url: inputURL)
guard let videoTrack = asset.tracks(withMediaType: .video).first else {
    fputs("Error: No video track found\n", stderr)
    exit(1)
}

let naturalSize = videoTrack.naturalSize
let duration = CMTimeGetSeconds(asset.duration)
let width = Int(naturalSize.width)
let height = Int(naturalSize.height)

let reader = try AVAssetReader(asset: asset)
let readerOutput = AVAssetReaderTrackOutput(track: videoTrack, outputSettings: [
    kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA
])
readerOutput.alwaysCopiesSampleData = false
reader.add(readerOutput)

let writer = try AVAssetWriter(outputURL: outputURL, fileType: .mp4)
let videoSettings: [String: Any] = [
    AVVideoCodecKey: AVVideoCodecType.h264,
    AVVideoWidthKey: width,
    AVVideoHeightKey: height,
    AVVideoCompressionPropertiesKey: [
        AVVideoAverageBitRateKey: 4_500_000,
        AVVideoProfileLevelKey: AVVideoProfileLevelH264HighAutoLevel
    ]
]
let writerInput = AVAssetWriterInput(mediaType: .video, outputSettings: videoSettings)
writerInput.expectsMediaDataInRealTime = false

let sourceBufferAttributes: [String: Any] = [
    kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA,
    kCVPixelBufferWidthKey as String: width,
    kCVPixelBufferHeightKey as String: height
]
let pixelBufferAdaptor = AVAssetWriterInputPixelBufferAdaptor(
    assetWriterInput: writerInput,
    sourcePixelBufferAttributes: sourceBufferAttributes
)

writer.add(writerInput)

let ciContext = CIContext(options: [
    .useSoftwareRenderer: false,
    .priorityRequestLow: false
])

let segRequest = VNGeneratePersonSegmentationRequest()
if qualityArg == "accurate" {
    segRequest.qualityLevel = .accurate
} else if qualityArg == "fast" {
    segRequest.qualityLevel = .fast
} else {
    segRequest.qualityLevel = .balanced
}
segRequest.outputPixelFormat = kCVPixelFormatType_OneComponent8

reader.startReading()
writer.startWriting()
writer.startSession(atSourceTime: .zero)

var frameCount = 0
let colorSpace = CGColorSpaceCreateDeviceRGB()
var pool: CVPixelBufferPool? = pixelBufferAdaptor.pixelBufferPool

while let sampleBuffer = readerOutput.copyNextSampleBuffer() {
    guard let imageBuffer = CMSampleBufferGetImageBuffer(sampleBuffer) else { continue }
    let presentationTime = CMSampleBufferGetPresentationTimeStamp(sampleBuffer)
    
    while !writerInput.isReadyForMoreMediaData {
        Thread.sleep(forTimeInterval: 0.005)
    }
    
    let originalCI = CIImage(cvImageBuffer: imageBuffer)
    
    let handler = VNImageRequestHandler(ciImage: originalCI, options: [:])
    try? handler.perform([segRequest])
    
    var outputCI = originalCI
    if let maskBuffer = segRequest.results?.first?.pixelBuffer {
        let rawMaskCI = CIImage(cvPixelBuffer: maskBuffer)
        let scaleX = originalCI.extent.width / rawMaskCI.extent.width
        let scaleY = originalCI.extent.height / rawMaskCI.extent.height
        let maskCI = rawMaskCI.transformed(by: CGAffineTransform(scaleX: scaleX, y: scaleY))
        
        let blurredCI = originalCI.clampedToExtent()
            .applyingFilter("CIGaussianBlur", parameters: ["inputRadius": blurRadius])
            .cropped(to: originalCI.extent)
        
        outputCI = originalCI.applyingFilter("CIBlendWithMask", parameters: [
            "inputBackgroundImage": blurredCI,
            "inputMaskImage": maskCI
        ])
    }
    
    var outputPixelBuffer: CVPixelBuffer?
    if pool == nil { pool = pixelBufferAdaptor.pixelBufferPool }
    if let p = pool {
        CVPixelBufferPoolCreatePixelBuffer(kCFAllocatorDefault, p, &outputPixelBuffer)
    }
    
    if let targetBuffer = outputPixelBuffer {
        ciContext.render(outputCI, to: targetBuffer, bounds: outputCI.extent, colorSpace: colorSpace)
        pixelBufferAdaptor.append(targetBuffer, withPresentationTime: presentationTime)
    }
    
    frameCount += 1
    if frameCount % 15 == 0 {
        let currentSeconds = CMTimeGetSeconds(presentationTime)
        let pct = duration > 0 ? min(99.0, round((currentSeconds / duration) * 100)) : 50.0
        print(String(format: "PROGRESS: %.1f%%", pct)); fflush(stdout)
    }
}

writerInput.markAsFinished()
let semaphore = DispatchSemaphore(value: 0)
writer.finishWriting {
    semaphore.signal()
}
semaphore.wait()

print("PROGRESS: 100.0%"); fflush(stdout)
print("SUCCESS: Video portrait blur finished!"); fflush(stdout)
