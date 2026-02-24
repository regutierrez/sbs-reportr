const DEFAULT_MAX_LONGEST_SIDE = 1000
const DEFAULT_QUALITY = 0.75

interface CompressionOptions {
  maxLongestSide?: number
  quality?: number
}

function buildJpegFileName(originalName: string): string {
  const suffixIndex = originalName.lastIndexOf('.')
  if (suffixIndex < 0) {
    return `${originalName}.jpg`
  }

  return `${originalName.slice(0, suffixIndex)}.jpg`
}

function loadImage(file: Blob): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const image = new Image()
    const objectUrl = URL.createObjectURL(file)

    image.onload = () => {
      URL.revokeObjectURL(objectUrl)
      resolve(image)
    }
    image.onerror = () => {
      URL.revokeObjectURL(objectUrl)
      reject(new Error('Unable to decode image file.'))
    }

    image.src = objectUrl
  })
}

function canvasToBlob(canvas: HTMLCanvasElement, quality: number): Promise<Blob> {
  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => {
        if (!blob) {
          reject(new Error('Unable to compress image.'))
          return
        }

        resolve(blob)
      },
      'image/jpeg',
      quality,
    )
  })
}

export async function compressImageForUpload(
  sourceFile: File,
  options: CompressionOptions = {},
): Promise<File> {
  const maxLongestSide = options.maxLongestSide ?? DEFAULT_MAX_LONGEST_SIDE
  const quality = options.quality ?? DEFAULT_QUALITY

  const image = await loadImage(sourceFile)
  const longestSide = Math.max(image.naturalWidth, image.naturalHeight)
  const scale = longestSide > maxLongestSide ? maxLongestSide / longestSide : 1

  const targetWidth = Math.max(1, Math.round(image.naturalWidth * scale))
  const targetHeight = Math.max(1, Math.round(image.naturalHeight * scale))

  const canvas = document.createElement('canvas')
  canvas.width = targetWidth
  canvas.height = targetHeight

  const context = canvas.getContext('2d')
  if (!context) {
    throw new Error('Unable to initialize image compression canvas.')
  }

  context.drawImage(image, 0, 0, targetWidth, targetHeight)
  const compressedBlob = await canvasToBlob(canvas, quality)

  return new File([compressedBlob], buildJpegFileName(sourceFile.name), {
    type: 'image/jpeg',
    lastModified: Date.now(),
  })
}
