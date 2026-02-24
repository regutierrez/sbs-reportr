import { afterEach, describe, expect, it, vi } from 'vitest'

import { compressImageForUpload } from '@/utils/image-compression'

describe('compressImageForUpload', () => {
  const originalImage = globalThis.Image

  afterEach(() => {
    vi.restoreAllMocks()
    globalThis.Image = originalImage
  })

  it('resizes to max side and outputs JPEG file', async () => {
    const drawImageMock = vi.fn()
    const fakeCanvas = {
      width: 0,
      height: 0,
      getContext: vi.fn(() => ({ drawImage: drawImageMock })),
      toBlob: vi.fn((callback: BlobCallback) => {
        callback(new Blob(['compressed'], { type: 'image/jpeg' }))
      }),
    } as unknown as HTMLCanvasElement

    const originalCreateElement = document.createElement.bind(document)
    const createElementSpy = vi.spyOn(document, 'createElement')
    createElementSpy.mockImplementation(((tagName: string) => {
      if (tagName === 'canvas') {
        return fakeCanvas
      }

      return originalCreateElement(tagName)
    }) as unknown as typeof document.createElement)

    class FakeImage {
      naturalWidth = 2000
      naturalHeight = 1000
      onload: (() => void) | null = null
      onerror: (() => void) | null = null

      set src(_value: string) {
        if (this.onload) {
          this.onload()
        }
      }
    }

    globalThis.Image = FakeImage as unknown as typeof Image

    vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:mock-image')
    const revokeSpy = vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {})

    const sourceFile = new File(['raw'], 'building.png', { type: 'image/png' })
    const compressed = await compressImageForUpload(sourceFile)

    expect(compressed.type).toBe('image/jpeg')
    expect(compressed.name).toBe('building.jpg')
    expect(fakeCanvas.width).toBe(1000)
    expect(fakeCanvas.height).toBe(500)
    expect(drawImageMock).toHaveBeenCalledTimes(1)
    expect(fakeCanvas.toBlob).toHaveBeenCalled()
    expect(revokeSpy).toHaveBeenCalledWith('blob:mock-image')
  })
})
