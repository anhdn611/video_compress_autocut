import Foundation
import AVFoundation
import CoreImage
import Vision

let inPath = "/Users/ngocanhdao/Downloads/IMG_3308.mov"
let inURL = URL(fileURLWithPath: inPath)
let asset = AVURLAsset(url: inURL)
guard let track = asset.tracks(withMediaType: .video).first else { exit(1) }

let reader = try! AVAssetReader(asset: asset)
let trackOut = AVAssetReaderTrackOutput(track: track, outputSettings: [kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA])
reader.add(trackOut)
reader.startReading()

var sample: CMSampleBuffer?
for _ in 0..<15 {
    if let s = trackOut.copyNextSampleBuffer() { sample = s } else { break }
}
reader.cancelReading()

guard let s = sample, let imgBuf = CMSampleBufferGetImageBuffer(s) else { exit(1) }
let origCI = CIImage(cvImageBuffer: imgBuf)
let ciContext = CIContext(options: [.useSoftwareRenderer: false])

// 1. Accurate Person Segmentation
let segReq = VNGeneratePersonSegmentationRequest()
segReq.qualityLevel = .accurate
segReq.outputPixelFormat = kCVPixelFormatType_OneComponent8

let handler = VNImageRequestHandler(ciImage: origCI, options: [:])
try? handler.perform([segReq])

guard let maskBuf = segReq.results?.first?.pixelBuffer else { exit(1) }
let rawMask = CIImage(cvPixelBuffer: maskBuf)

// Scale raw mask to match original size
let sx = origCI.extent.width / rawMask.extent.width
let sy = origCI.extent.height / rawMask.extent.height
let scaledMask = rawMask.transformed(by: CGAffineTransform(scaleX: sx, y: sy))

// TEST 1: Current Naive Method (Balanced or raw scale)
let blurRad = 25.0
let blurredNaive = origCI.clampedToExtent().applyingFilter("CIGaussianBlur", parameters: ["inputRadius": blurRad]).cropped(to: origCI.extent)
let blendedNaive = origCI.applyingFilter("CIBlendWithMask", parameters: ["inputBackgroundImage": blurredNaive, "inputMaskImage": scaledMask])
try? ciContext.writeJPEGRepresentation(of: blendedNaive, to: URL(fileURLWithPath: "test_naive.jpg"), colorSpace: CGColorSpaceCreateDeviceRGB(), options: [:])

// TEST 2: Guided Filter Upsampling + Mask Edge Snapping
// CIGuidedFilter takes inputImage (small mask) and inputGuideImage (original high-res)
var refinedMask = scaledMask
if let gf = CIFilter(name: "CIGuidedFilter") {
    gf.setValue(rawMask, forKey: "inputImage")
    gf.setValue(origCI, forKey: "inputGuideImage")
    gf.setValue(3.0, forKey: "inputRadius")
    gf.setValue(0.0001, forKey: "inputEpsilon")
    if let out = gf.outputImage {
        refinedMask = out
    }
}

// Enhance mask contrast with S-curve/ColorControls to make body 100% solid and remove semi-transparent edge bleed
let contrastMask = refinedMask.applyingFilter("CIColorControls", parameters: [
    "inputContrast": 1.4,
    "inputBrightness": 0.05
]).clampedToExtent().cropped(to: origCI.extent)

// TEST 3: Preventing Foreground Color Bleed into Background
// When blurring background, we replace the foreground with slightly dilated background or clamp
// Let's create an inverted mask for background
let invertedMask = contrastMask.applyingFilter("CIColorInvert")

// Now test CIMaskedVariableBlur with the inverted mask
var variableBlurred = origCI
if let mvb = CIFilter(name: "CIMaskedVariableBlur") {
    mvb.setValue(origCI, forKey: "inputImage")
    mvb.setValue(invertedMask, forKey: "inputMask")
    mvb.setValue(blurRad, forKey: "inputRadius")
    if let out = mvb.outputImage {
        variableBlurred = out
    }
}
try? ciContext.writeJPEGRepresentation(of: variableBlurred, to: URL(fileURLWithPath: "test_variable_blur.jpg"), colorSpace: CGColorSpaceCreateDeviceRGB(), options: [:])

// TEST 4: Guided Mask + Clean Blend
let cleanBlend = origCI.applyingFilter("CIBlendWithMask", parameters: [
    "inputBackgroundImage": blurredNaive,
    "inputMaskImage": contrastMask
])
try? ciContext.writeJPEGRepresentation(of: cleanBlend, to: URL(fileURLWithPath: "test_guided_blend.jpg"), colorSpace: CGColorSpaceCreateDeviceRGB(), options: [:])

print("TESTS_COMPLETED")
