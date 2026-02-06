<script setup>
import { ref, onMounted, onUnmounted, watchEffect, computed, watch, nextTick } from 'vue'
import { decompressFrames, parseGIF } from 'gifuct-js'

const props = defineProps({
  bannerUrl: String,
  welcomeText: {
    type: String,
    default: 'WELCOME'
  },
  text: {
    type: String,
    default: 'Welcome {user}!'
  },
  textColor: {
    type: String,
    default: '#FFD700'
  },
  profilePosition: {
    type: String,
    default: 'center'
  },
  fontFamily: {
    type: String,
    default: 'arial'
  },
  avatarOffsetX: {
    type: Number,
    default: 0
  },
  avatarOffsetY: {
    type: Number,
    default: 0
  },
  textOffsetX: {
    type: Number,
    default: 0
  },
  textOffsetY: {
    type: Number,
    default: 0
  },
  welcomeTextSize: {
    type: Number,
    default: 56
  },
  usernameTextSize: {
    type: Number,
    default: 32
  },
  avatarSize: {
    type: Number,
    default: 180
  },
  // Text style props for welcome text
  welcomeTextBold: {
    type: Boolean,
    default: false
  },
  welcomeTextItalic: {
    type: Boolean,
    default: false
  },
  welcomeTextUnderline: {
    type: Boolean,
    default: false
  },
  // Text style props for username text
  usernameTextBold: {
    type: Boolean,
    default: false
  },
  usernameTextItalic: {
    type: Boolean,
    default: false
  },
  usernameTextUnderline: {
    type: Boolean,
    default: false
  },
  // Google Font and custom font props
  googleFontFamily: {
    type: String,
    default: null
  },
  customFontPath: {
    type: String,
    default: null
  },
  // Avatar shape prop
  avatarShape: {
    type: String,
    default: 'circle'
  },
  // Avatar border props
  avatarBorderEnabled: {
    type: Boolean,
    default: true
  },
  avatarBorderWidth: {
    type: Number,
    default: 6
  },
  avatarBorderColor: {
    type: String,
    default: '#FFFFFF'
  }
})

const emit = defineEmits(['update:avatarOffsetX', 'update:avatarOffsetY', 'update:textOffsetX', 'update:textOffsetY'])

// GIF support state
const isGif = ref(false)
const gifFrames = ref([])  // Store decoded frame data for live preview
const currentFrame = ref(0)
const isPlaying = ref(false)
const totalFrames = ref(0)
const gifLoaded = ref(false)
let playInterval = null
const gifImage = ref(null)
const showAnimatedPreview = ref(false) // Toggle between canvas and animated preview

// Live preview animation state
const liveCanvasRef = ref(null)  // Canvas for avatar/text overlay
const liveImageRef = ref(null)  // Native img for smooth GIF animation
const currentLiveFrame = ref(0)  // Current frame index for animation
let liveAnimationTimeout = null  // Timeout for next frame
const isLivePreviewLoading = ref(false)  // Loading state for live preview
let overlayRenderInterval = null  // Interval for re-rendering overlay

// Check if URL is a GIF
const checkIsGif = (url) => {
  if (!url) return false
  const urlLower = url.toLowerCase()
  return urlLower.includes('.gif') || urlLower.includes('format=gif')
}

// Load GIF and extract frames using gifuct-js
const loadGifFrames = async (url) => {
  if (!checkIsGif(url)) {
    isGif.value = false
    gifLoaded.value = false
    return
  }

  isGif.value = true
  gifLoaded.value = false
  isLivePreviewLoading.value = true

  try {
    // Fetch GIF as array buffer (add mode: 'cors' for external URLs)
    const response = await fetch(url, { mode: 'cors' })
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    const arrayBuffer = await response.arrayBuffer()
    console.log('GIF arrayBuffer size:', arrayBuffer.byteLength)

    // Parse using gifuct-js
    const gifData = parseGIF(arrayBuffer)
    const rawFrames = decompressFrames(gifData, true)

    console.log('GIF parsed:', { width: gifData.lsd.width, height: gifData.lsd.height, frames: rawFrames.length })

    // Process frames - convert to canvas elements with proper disposal handling
    const CANVAS_WIDTH = 1000
    const CANVAS_HEIGHT = 400
    const GIF_WIDTH = gifData.lsd.width
    const GIF_HEIGHT = gifData.lsd.height

    // Working canvas at original GIF size
    const workCanvas = document.createElement('canvas')
    workCanvas.width = GIF_WIDTH
    workCanvas.height = GIF_HEIGHT
    const workCtx = workCanvas.getContext('2d')

    // Get the global color table for transparent color handling
    const gct = gifData.gct && gifData.gct.colors ? gifData.gct.colors : []
    const backgroundColorIndex = gifData.lsd.bgColor
    const backgroundColor = gct[backgroundColorIndex]
      ? `rgb(${gct[backgroundColorIndex][0]}, ${gct[backgroundColorIndex][1]}, ${gct[backgroundColorIndex][2]})`
      : '#000000'

    // Clear to background color initially
    workCtx.fillStyle = backgroundColor
    workCtx.fillRect(0, 0, GIF_WIDTH, GIF_HEIGHT)

    // Store previous canvas for disposal type 3
    let previousCanvas = null

    const frameCanvases = []

    for (let i = 0; i < rawFrames.length; i++) {
      const frame = rawFrames[i]

      // Apply disposal from PREVIOUS frame before drawing current one
      if (i > 0) {
        const prevFrame = rawFrames[i - 1]
        if (prevFrame.disposalType === 2) {
          // Restore to background - fill with background color
          workCtx.fillStyle = backgroundColor
          workCtx.fillRect(0, 0, GIF_WIDTH, GIF_HEIGHT)
        } else if (prevFrame.disposalType === 3 && previousCanvas) {
          // Restore to previous state
          workCtx.clearRect(0, 0, GIF_WIDTH, GIF_HEIGHT)
          workCtx.drawImage(previousCanvas, 0, 0)
        }
      }

      // Save current state BEFORE drawing (for disposal type 3 of next frame)
      const beforeDrawCanvas = document.createElement('canvas')
      beforeDrawCanvas.width = GIF_WIDTH
      beforeDrawCanvas.height = GIF_HEIGHT
      beforeDrawCanvas.getContext('2d').drawImage(workCanvas, 0, 0)

      // Create Image from the patch data and draw it (handles transparency correctly)
      const patchCanvas = document.createElement('canvas')
      patchCanvas.width = frame.dims.width
      patchCanvas.height = frame.dims.height
      const patchCtx = patchCanvas.getContext('2d')

      // Put the image data on the patch canvas
      const imageData = new ImageData(
        new Uint8ClampedArray(frame.patch),
        frame.dims.width,
        frame.dims.height
      )
      patchCtx.putImageData(imageData, 0, 0)

      // Draw the patch onto the work canvas (this handles transparency correctly)
      workCtx.drawImage(patchCanvas, frame.dims.left, frame.dims.top)

      // Create output canvas for this frame (scaled to preview size)
      const frameCanvas = document.createElement('canvas')
      frameCanvas.width = CANVAS_WIDTH
      frameCanvas.height = CANVAS_HEIGHT
      const frameCtx = frameCanvas.getContext('2d')

      // Fill background
      frameCtx.fillStyle = '#2b2d31'
      frameCtx.fillRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT)

      // Scale and draw
      const scale = Math.max(CANVAS_WIDTH / GIF_WIDTH, CANVAS_HEIGHT / GIF_HEIGHT)
      const x = (CANVAS_WIDTH - GIF_WIDTH * scale) / 2
      const y = (CANVAS_HEIGHT - GIF_HEIGHT * scale) / 2
      frameCtx.drawImage(workCanvas, x, y, GIF_WIDTH * scale, GIF_HEIGHT * scale)

      // gifuct-js returns delay in centiseconds (1/100s), convert to ms
      const delayMs = (frame.delay || 6) * 10

      frameCanvases.push({
        canvas: frameCanvas,
        delay: delayMs
      })

      // Save for next frame's disposal type 3
      previousCanvas = beforeDrawCanvas
    }

    console.log('GIF frames loaded:', frameCanvases.length)

    gifFrames.value = frameCanvases
    totalFrames.value = frameCanvases.length
    currentLiveFrame.value = 0
    gifLoaded.value = true

    // Load the first frame for edit mode preview
    const img = new Image()
    img.crossOrigin = 'anonymous'
    await new Promise((resolve) => {
      img.onload = () => {
        gifImage.value = img
        resolve()
      }
      img.onerror = () => resolve()
      img.src = url
    })
  } catch (e) {
    console.error('Failed to load GIF:', e)
    // Don't set isGif to false - keep it true but mark as error
    gifLoaded.value = false
    previewError.value = true
  } finally {
    isLivePreviewLoading.value = false
  }
}

// GIF playback controls
const togglePlayPause = () => {
  if (isPlaying.value) {
    pauseGif()
  } else {
    playGif()
  }
}

const playGif = () => {
  if (!isGif.value || totalFrames.value <= 1) return
  isPlaying.value = true
  playInterval = setInterval(() => {
    currentFrame.value = (currentFrame.value + 1) % totalFrames.value
  }, 100) // 100ms per frame (10fps)
}

const pauseGif = () => {
  isPlaying.value = false
  if (playInterval) {
    clearInterval(playInterval)
    playInterval = null
  }
}

const prevFrame = () => {
  pauseGif()
  if (totalFrames.value > 0) {
    currentFrame.value = (currentFrame.value - 1 + totalFrames.value) % totalFrames.value
  }
}

const nextFrame = () => {
  pauseGif()
  if (totalFrames.value > 0) {
    currentFrame.value = (currentFrame.value + 1) % totalFrames.value
  }
}

// Clean up interval on unmount
const cleanup = () => {
  pauseGif()
  if (liveAnimationTimeout) {
    clearTimeout(liveAnimationTimeout)
    liveAnimationTimeout = null
  }
  if (overlayRenderInterval) {
    cancelAnimationFrame(overlayRenderInterval)
    overlayRenderInterval = null
  }
  if (dragAnimationId) {
    cancelAnimationFrame(dragAnimationId)
    dragAnimationId = null
  }
}

// Font mapping to CSS font family names
const getFontFamily = (font) => {
  const fontMap = {
    'arial': 'Arial, sans-serif',
    'arialblack': '"Arial Black", sans-serif',
    'impact': 'Impact, sans-serif',
    'verdana': 'Verdana, sans-serif',
    'comic': '"Comic Sans MS", cursive, sans-serif',
    'georgia': 'Georgia, serif',
    'times': '"Times New Roman", Times, serif',
    'courier': '"Courier New", monospace',
    'segoe': '"Segoe UI", sans-serif',
    'tahoma': 'Tahoma, sans-serif',
    'trebuchet': '"Trebuchet MS", sans-serif',
    'calibri': 'Calibri, sans-serif',
    'cambria': 'Cambria, serif',
    'consolas': 'Consolas, monospace',
    'lucida': '"Lucida Console", monospace',
    'palatino': '"Palatino Linotype", "Book Antiqua", Palatino, serif',
    'century': 'Century, serif',
    'rockwell': 'Rockwell, serif',
    'franklin': '"Franklin Gothic Medium", "Arial Narrow", Arial, sans-serif',
    // Google Fonts
    'roboto': 'Roboto, sans-serif',
    'poppins': 'Poppins, sans-serif',
    'montserrat': 'Montserrat, sans-serif',
    'opensans': '"Open Sans", sans-serif',
    'lato': 'Lato, sans-serif',
    'oswald': 'Oswald, sans-serif',
    'raleway': 'Raleway, sans-serif',
    'ptsans': '"PT Sans", sans-serif',
    'nunito': 'Nunito, sans-serif',
    'bebasneue': '"Bebas Neue", cursive, sans-serif'
  }
  return fontMap[font] || 'Arial, sans-serif'
}

// Function to load Google Fonts dynamically
const loadGoogleFont = (fontName) => {
  if (!fontName) return

  const googleFontMap = {
    'roboto': 'Roboto:wght@400;700;ital@0;1',
    'poppins': 'Poppins:wght@400;700;ital@0;1',
    'montserrat': 'Montserrat:wght@400;700;ital@0;1',
    'opensans': 'Open+Sans:wght@400;700;ital@0;1',
    'lato': 'Lato:wght@400;700;ital@0;1',
    'oswald': 'Oswald:wght@400;700;ital@0;1',
    'raleway': 'Raleway:wght@400;700;ital@0;1',
    'ptsans': 'PT+Sans:wght@400;700;ital@0;1',
    'nunito': 'Nunito:wght@400;700;ital@0;1',
    'bebasneue': 'Bebas+Neue:wght@400;700'
  }

  const googleFontName = googleFontMap[fontName.toLowerCase()]
  if (googleFontName && !document.querySelector(`link[href*="fonts.googleapis.com/css?family=${googleFontName}"]`)) {
    const link = document.createElement('link')
    link.href = `https://fonts.googleapis.com/css2?family=${googleFontName}&display=swap`
    link.rel = 'stylesheet'
    document.head.appendChild(link)
  }
}

// Load Google Fonts on mount if a Google Font is selected
if (props.googleFontFamily) {
  loadGoogleFont(props.googleFontFamily)
}

// Watch for changes in Google Font family
watch(() => props.googleFontFamily, (newFont) => {
  if (newFont) {
    loadGoogleFont(newFont)
  }
})

// Helper function to build font string with style
const buildFontString = (size, family, bold, italic) => {
  const style = italic ? 'italic' : 'normal'
  const weight = bold ? 'bold' : 'normal'
  return `${style} ${weight} ${size}px ${getFontFamily(family)}`
}

// Helper function to draw underline
const drawUnderline = (ctx, text, x, y, fontSize, color, isBold) => {
  const metrics = ctx.measureText(text)
  const width = metrics.width
  const underlineY = y + fontSize + 4
  const underlineWidth = Math.max(2, Math.floor(fontSize / 12))

  // Draw underline
  ctx.fillStyle = color
  ctx.fillRect(x - width / 2 - 2, underlineY, width + 4, underlineWidth)
}

// Helper function to draw avatar shape (border)
const drawAvatarShapeBorder = (ctx, x, y, size, borderWidth) => {
  const shape = props.avatarShape || 'circle'
  const centerX = x + size / 2
  const centerY = y + size / 2
  const outerSize = size + borderWidth * 2
  const outerX = x - borderWidth
  const outerY = y - borderWidth
  const halfOuter = outerSize / 2
  const halfInner = size / 2

  ctx.beginPath()

  switch (shape.toLowerCase()) {
    case 'square':
      ctx.rect(outerX, outerY, outerSize, outerSize)
      break

    case 'rounded':
      const rRadius = outerSize / 6
      ctx.roundRect(outerX, outerY, outerSize, outerSize, rRadius)
      break

    case 'squircle':
      const sRadius = outerSize / 3
      ctx.roundRect(outerX, outerY, outerSize, outerSize, sRadius)
      break

    case 'hexagon':
      for (let i = 0; i < 6; i++) {
        const angle = 60 * i - 30
        const px = centerX + halfOuter * Math.cos(Math.PI * angle / 180)
        const py = centerY + halfOuter * Math.sin(Math.PI * angle / 180)
        if (i === 0) ctx.moveTo(px, py)
        else ctx.lineTo(px, py)
      }
      ctx.closePath()
      break

    case 'star':
      for (let i = 0; i < 10; i++) {
        const angle = 36 * i - 90
        const radius = i % 2 === 0 ? halfOuter : outerSize / 4
        const px = centerX + radius * Math.cos(Math.PI * angle / 180)
        const py = centerY + radius * Math.sin(Math.PI * angle / 180)
        if (i === 0) ctx.moveTo(px, py)
        else ctx.lineTo(px, py)
      }
      ctx.closePath()
      break

    case 'diamond':
      ctx.moveTo(centerX, outerY)
      ctx.lineTo(x + outerSize, centerY)
      ctx.lineTo(centerX, y + outerSize)
      ctx.lineTo(outerX, centerY)
      ctx.closePath()
      break

    case 'triangle':
      ctx.moveTo(centerX, outerY)
      ctx.lineTo(x + outerSize, y + outerSize)
      ctx.lineTo(outerX, y + outerSize)
      ctx.closePath()
      break

    case 'circle':
    default:
      ctx.arc(centerX, centerY, halfOuter, 0, Math.PI * 2)
      break
  }

  ctx.fillStyle = props.avatarBorderColor || '#FFFFFF'
  ctx.fill()
}

// Helper function to draw avatar shape (inner)
const drawAvatarShapeInner = (ctx, x, y, size) => {
  const shape = props.avatarShape || 'circle'
  const centerX = x + size / 2
  const centerY = y + size / 2
  const halfSize = size / 2

  ctx.beginPath()

  switch (shape.toLowerCase()) {
    case 'square':
      ctx.rect(x, y, size, size)
      break

    case 'rounded':
      const rRadius = size / 6
      ctx.roundRect(x, y, size, size, rRadius)
      break

    case 'squircle':
      const sRadius = size / 3
      ctx.roundRect(x, y, size, size, sRadius)
      break

    case 'hexagon':
      for (let i = 0; i < 6; i++) {
        const angle = 60 * i - 30
        const px = centerX + halfSize * Math.cos(Math.PI * angle / 180)
        const py = centerY + halfSize * Math.sin(Math.PI * angle / 180)
        if (i === 0) ctx.moveTo(px, py)
        else ctx.lineTo(px, py)
      }
      ctx.closePath()
      break

    case 'star':
      for (let i = 0; i < 10; i++) {
        const angle = 36 * i - 90
        const radius = i % 2 === 0 ? halfSize : size / 4
        const px = centerX + radius * Math.cos(Math.PI * angle / 180)
        const py = centerY + radius * Math.sin(Math.PI * angle / 180)
        if (i === 0) ctx.moveTo(px, py)
        else ctx.lineTo(px, py)
      }
      ctx.closePath()
      break

    case 'diamond':
      ctx.moveTo(centerX, y)
      ctx.lineTo(x + size, centerY)
      ctx.lineTo(centerX, y + size)
      ctx.lineTo(x, centerY)
      ctx.closePath()
      break

    case 'triangle':
      ctx.moveTo(centerX, y)
      ctx.lineTo(x + size, y + size)
      ctx.lineTo(x, y + size)
      ctx.closePath()
      break

    case 'circle':
    default:
      ctx.arc(centerX, centerY, halfSize, 0, Math.PI * 2)
      break
  }

  ctx.fillStyle = '#5865f2'
  ctx.fill()
}

// Reusable function to draw avatar and text overlay
const drawAvatarAndText = (ctx, CANVAS_WIDTH, CANVAS_HEIGHT) => {
  const avatarSize = props.avatarSize || 180
  const borderEnabled = props.avatarBorderEnabled !== undefined ? props.avatarBorderEnabled : true
  const borderWidth = borderEnabled ? (props.avatarBorderWidth || 6) : 0
  const totalAvatarSize = avatarSize + borderWidth * 2

  // Calculate avatar position
  let avatarX, avatarY
  const position = props.profilePosition || 'center'

  if (position === 'center') {
    avatarX = (CANVAS_WIDTH - totalAvatarSize) / 2
    avatarY = (CANVAS_HEIGHT - totalAvatarSize) / 2 - 40
  } else if (position === 'left') {
    avatarX = 30
    avatarY = (CANVAS_HEIGHT - totalAvatarSize) / 2 - 40
  } else if (position === 'right') {
    avatarX = CANVAS_WIDTH - totalAvatarSize - 30
    avatarY = (CANVAS_HEIGHT - totalAvatarSize) / 2 - 40
  } else {
    avatarX = (CANVAS_WIDTH - totalAvatarSize) / 2
    avatarY = (CANVAS_HEIGHT - totalAvatarSize) / 2 - 40
  }

  // Apply manual offset
  avatarX += (props.avatarOffsetX || 0)
  avatarY += (props.avatarOffsetY || 0)

  // Text position
  const BASE_TEXT_Y = 120
  const BASE_TEXT_X = CANVAS_WIDTH / 2
  let textX = BASE_TEXT_X + (props.textOffsetX || 0)
  let textY = BASE_TEXT_Y + (props.textOffsetY || 0)

  // Get font family
  const fontFamily = getFontFamily(props.fontFamily || 'arial')

  // Draw welcome text with shadow
  const welcomeFontSize = props.welcomeTextSize || 56
  const welcomeBold = props.welcomeTextBold || false
  const welcomeItalic = props.welcomeTextItalic || false
  const welcomeUnderline = props.welcomeTextUnderline || false

  ctx.font = buildFontString(welcomeFontSize, props.fontFamily || 'arial', welcomeBold, welcomeItalic)
  ctx.textAlign = 'center'
  ctx.textBaseline = 'top'

  const welcomeTextUpper = (props.welcomeText || 'WELCOME').toUpperCase()

  // Shadow
  ctx.fillStyle = '#000000'
  ctx.fillText(welcomeTextUpper, textX + 3, textY + 3)

  // Main text
  ctx.fillStyle = props.textColor || '#FFD700'
  ctx.fillText(welcomeTextUpper, textX, textY)

  // Draw underline if enabled
  if (welcomeUnderline) {
    drawUnderline(ctx, welcomeTextUpper, textX, textY, welcomeFontSize, props.textColor || '#FFD700', welcomeBold)
  }

  // Draw username with shadow
  const usernameFontSize = props.usernameTextSize || 32
  const usernameBold = props.usernameTextBold || false
  const usernameItalic = props.usernameTextItalic || false
  const usernameUnderline = props.usernameTextUnderline || false

  ctx.font = buildFontString(usernameFontSize, props.fontFamily || 'arial', usernameBold, usernameItalic)
  const usernameY = textY + welcomeFontSize + 10

  const usernameTextUpper = usernameText.value.toUpperCase()

  // Shadow
  ctx.fillStyle = '#000000'
  ctx.fillText(usernameTextUpper, textX + 2, usernameY + 2)

  // Main text
  ctx.fillStyle = '#ffffff'
  ctx.fillText(usernameTextUpper, textX, usernameY)

  // Draw underline if enabled
  if (usernameUnderline) {
    drawUnderline(ctx, usernameTextUpper, textX, usernameY, usernameFontSize, '#ffffff', usernameBold)
  }

  // Draw shaped avatar border (only if enabled)
  if (borderEnabled) {
    drawAvatarShapeBorder(ctx, avatarX, avatarY, totalAvatarSize, borderWidth)
  }

  // Draw shaped avatar inner
  drawAvatarShapeInner(ctx, avatarX + borderWidth, avatarY + borderWidth, avatarSize)

  // Avatar silhouette (centered on the shape)
  ctx.fillStyle = '#ffffff'
  const centerX = avatarX + totalAvatarSize / 2
  const centerY = avatarY + totalAvatarSize / 2

  // Head
  ctx.beginPath()
  ctx.arc(centerX, centerY - 15, 25, 0, Math.PI * 2)
  ctx.fill()

  // Body (shoulders)
  ctx.beginPath()
  ctx.arc(centerX, centerY + 30, 35, Math.PI, 0)
  ctx.fill()
}

// Live preview - render overlay canvas on top of native GIF
const renderLiveOverlay = () => {
  if (!showAnimatedPreview.value || !liveCanvasRef.value) {
    return
  }

  const canvas = liveCanvasRef.value
  const ctx = canvas.getContext('2d')

  // Clear canvas (transparent - let the GIF show through)
  ctx.clearRect(0, 0, canvas.width, canvas.height)

  // Draw avatar and text overlay only
  drawAvatarAndText(ctx, canvas.width, canvas.height)

  // Keep re-rendering to sync with GIF animation
  overlayRenderInterval = requestAnimationFrame(renderLiveOverlay)
}

// Start live preview animation
const animateLivePreview = () => {
  if (!showAnimatedPreview.value) {
    return
  }

  const canvas = liveCanvasRef.value
  const img = liveImageRef.value

  if (!canvas || !img) {
    // Retry after a short delay
    nextTick(() => {
      if (liveCanvasRef.value && liveImageRef.value) {
        animateLivePreview()
      }
    })
    return
  }

  console.log('Starting live preview with native GIF + overlay')

  // Start rendering the overlay
  renderLiveOverlay()
}

const canvasRef = ref(null)
const isGenerating = ref(false)
const previewError = ref(false)
const showGrid = ref(true)
const usernameText = ref('USERNAME')

// Drag state
const isDragging = ref(false)
const dragTarget = ref(null) // 'avatar' or 'text'
const dragStartPos = ref({ x: 0, y: 0 })
const elementStartPos = ref({ x: 0, y: 0 })
const currentAvatarX = ref(0)
const currentAvatarY = ref(0)
const textOffsetX = ref(0)
const textOffsetY = ref(0)

// Smart guide state - tracks which grid lines elements are snapped to
const smartGuides = ref({
  avatar: { verticalX: null, horizontalY: null },
  text: { verticalX: null, horizontalY: null }
})

// Store element bounds for hit detection
const elementBounds = ref({
  avatar: { x: 0, y: 0, width: 0, height: 0 },
  welcomeText: { x: 0, y: 0, width: 0, height: 0 }
})

// Offscreen canvas for caching static background (prevents flicker during drag)
const offscreenCanvas = ref(null)
const isCacheValid = ref(false)
const cachedBannerUrl = ref(null)
const cachedShowGrid = ref(false)
// Track RAF for drag rendering
let dragAnimationId = null

// Build or rebuild the background cache (static elements: bg image + overlay + grid)
const buildBackgroundCache = async () => {
  if (!canvasRef.value) return false

  const CANVAS_WIDTH = 1000
  const CANVAS_HEIGHT = 400

  // Create offscreen canvas if needed
  if (!offscreenCanvas.value) {
    offscreenCanvas.value = document.createElement('canvas')
    offscreenCanvas.value.width = CANVAS_WIDTH
    offscreenCanvas.value.height = CANVAS_HEIGHT
  }

  const cacheCtx = offscreenCanvas.value.getContext('2d')

  // Fill background
  cacheCtx.fillStyle = '#2b2d31'
  cacheCtx.fillRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT)

  // Load and draw banner image
  if (props.bannerUrl) {
    const useImg = (isGif.value && gifImage.value) ? gifImage.value : new Image()
    if (!isGif.value || !gifImage.value) {
      useImg.crossOrigin = 'anonymous'
    }

    await new Promise((resolve, reject) => {
      if (useImg.complete && gifLoaded.value) {
        drawImageToCanvas(useImg)
        resolve()
      } else {
        useImg.onload = () => {
          drawImageToCanvas(useImg)
          resolve()
        }
        useImg.onerror = () => reject(new Error('Failed to load image'))
        if (!gifLoaded.value) {
          useImg.src = props.bannerUrl
        }
      }
    })

    function drawImageToCanvas(img) {
      const scale = Math.max(CANVAS_WIDTH / img.width, CANVAS_HEIGHT / img.height)
      const x = (CANVAS_WIDTH - img.width * scale) / 2
      const y = (CANVAS_HEIGHT - img.height * scale) / 2
      cacheCtx.drawImage(img, x, y, img.width * scale, img.height * scale)
    }
  }

  // Add overlay
  cacheCtx.fillStyle = 'rgba(0, 0, 0, 0.2)'
  cacheCtx.fillRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT)

  // Draw grid if enabled
  if (showGrid.value) {
    cacheCtx.strokeStyle = 'rgba(255, 255, 255, 0.15)'
    cacheCtx.lineWidth = 1

    // Vertical lines
    for (let x = 0; x <= CANVAS_WIDTH; x += 50) {
      cacheCtx.beginPath()
      cacheCtx.moveTo(x, 0)
      cacheCtx.lineTo(x, CANVAS_HEIGHT)
      cacheCtx.stroke()
    }

    // Horizontal lines
    for (let y = 0; y <= CANVAS_HEIGHT; y += 50) {
      cacheCtx.beginPath()
      cacheCtx.moveTo(0, y)
      cacheCtx.lineTo(CANVAS_WIDTH, y)
      cacheCtx.stroke()
    }

    // Center lines
    cacheCtx.strokeStyle = 'rgba(255, 255, 255, 0.3)'
    cacheCtx.beginPath()
    cacheCtx.moveTo(CANVAS_WIDTH / 2, 0)
    cacheCtx.lineTo(CANVAS_WIDTH / 2, CANVAS_HEIGHT)
    cacheCtx.stroke()
    cacheCtx.beginPath()
    cacheCtx.moveTo(0, CANVAS_HEIGHT / 2)
    cacheCtx.lineTo(CANVAS_WIDTH, CANVAS_HEIGHT / 2)
    cacheCtx.stroke()
  }

  // Update cache state
  cachedBannerUrl.value = props.bannerUrl
  cachedShowGrid.value = showGrid.value
  isCacheValid.value = true
  return true
}

// Fast drag render - uses cached background, only redraws moving elements
const renderDragPreview = () => {
  if (!canvasRef.value) return

  const canvas = canvasRef.value
  const ctx = canvas.getContext('2d')
  const CANVAS_WIDTH = 1000
  const CANVAS_HEIGHT = 400

  // Ensure canvas size is set without clearing (only if needed)
  if (canvas.width !== CANVAS_WIDTH || canvas.height !== CANVAS_HEIGHT) {
    canvas.width = CANVAS_WIDTH
    canvas.height = CANVAS_HEIGHT
  }

  // Copy cached background to main canvas (instant - no async operations)
  if (offscreenCanvas.value && isCacheValid.value) {
    ctx.drawImage(offscreenCanvas.value, 0, 0)
  } else {
    // Fallback: fill with background color
    ctx.fillStyle = '#2b2d31'
    ctx.fillRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT)
  }

  // Get font family
  const fontFamily = getFontFamily(props.fontFamily || 'arial')

  // Calculate positions
  const avatarSize = props.avatarSize || 180
  const borderEnabled = props.avatarBorderEnabled !== undefined ? props.avatarBorderEnabled : true
  const borderWidth = borderEnabled ? (props.avatarBorderWidth || 6) : 0
  const totalAvatarSize = avatarSize + borderWidth * 2

  let avatarX, avatarY
  const position = props.profilePosition || 'center'

  if (position === 'center') {
    avatarX = (CANVAS_WIDTH - totalAvatarSize) / 2
    avatarY = (CANVAS_HEIGHT - totalAvatarSize) / 2 - 40
  } else if (position === 'left') {
    avatarX = 30
    avatarY = (CANVAS_HEIGHT - totalAvatarSize) / 2 - 40
  } else if (position === 'right') {
    avatarX = CANVAS_WIDTH - totalAvatarSize - 30
    avatarY = (CANVAS_HEIGHT - totalAvatarSize) / 2 - 40
  } else {
    avatarX = (CANVAS_WIDTH - totalAvatarSize) / 2
    avatarY = (CANVAS_HEIGHT - totalAvatarSize) / 2 - 40
  }

  // Use current drag position
  avatarX += currentAvatarX.value
  avatarY += currentAvatarY.value

  // Text position
  const BASE_TEXT_Y = 120
  const BASE_TEXT_X = CANVAS_WIDTH / 2
  let textX = BASE_TEXT_X + textOffsetX.value
  let textY = BASE_TEXT_Y + textOffsetY.value

  // Draw smart guides
  if (isDragging.value) {
    ctx.strokeStyle = '#00D9FF'
    ctx.lineWidth = 2
    ctx.setLineDash([8, 4])

    const avatarCenterX = avatarX + totalAvatarSize / 2
    const avatarCenterY = avatarY + totalAvatarSize / 2

    if (smartGuides.value.avatar.verticalX !== null) {
      ctx.beginPath()
      ctx.moveTo(avatarCenterX, 0)
      ctx.lineTo(avatarCenterX, CANVAS_HEIGHT)
      ctx.stroke()
      ctx.fillStyle = '#00D9FF'
      ctx.beginPath()
      ctx.arc(avatarCenterX, avatarCenterY, 5, 0, Math.PI * 2)
      ctx.fill()
    }

    if (smartGuides.value.avatar.horizontalY !== null) {
      ctx.beginPath()
      ctx.moveTo(0, avatarCenterY)
      ctx.lineTo(CANVAS_WIDTH, avatarCenterY)
      ctx.stroke()
      ctx.fillStyle = '#00D9FF'
      ctx.beginPath()
      ctx.arc(avatarCenterX, avatarCenterY, 5, 0, Math.PI * 2)
      ctx.fill()
    }

    const textCenterX = textX
    const textCenterY = textY + 30

    if (smartGuides.value.text.verticalX !== null) {
      ctx.beginPath()
      ctx.moveTo(textCenterX, 0)
      ctx.lineTo(textCenterX, CANVAS_HEIGHT)
      ctx.stroke()
      ctx.fillStyle = '#00D9FF'
      ctx.beginPath()
      ctx.arc(textCenterX, textCenterY, 5, 0, Math.PI * 2)
      ctx.fill()
    }

    if (smartGuides.value.text.horizontalY !== null) {
      ctx.beginPath()
      ctx.moveTo(0, textCenterY)
      ctx.lineTo(CANVAS_WIDTH, textCenterY)
      ctx.stroke()
      ctx.fillStyle = '#00D9FF'
      ctx.beginPath()
      ctx.arc(textCenterX, textCenterY, 5, 0, Math.PI * 2)
      ctx.fill()
    }

    ctx.setLineDash([])
  }

  // Draw welcome text
  const welcomeFontSize = props.welcomeTextSize || 56
  const welcomeBold = props.welcomeTextBold || false
  const welcomeItalic = props.welcomeTextItalic || false
  const welcomeUnderline = props.welcomeTextUnderline || false

  ctx.font = buildFontString(welcomeFontSize, props.fontFamily || 'arial', welcomeBold, welcomeItalic)
  ctx.textAlign = 'center'
  ctx.textBaseline = 'top'

  const welcomeTextUpper = (props.welcomeText || 'WELCOME').toUpperCase()

  ctx.fillStyle = '#000000'
  ctx.fillText(welcomeTextUpper, textX + 3, textY + 3)

  ctx.fillStyle = props.textColor || '#FFD700'
  ctx.fillText(welcomeTextUpper, textX, textY)

  // Draw underline if enabled
  if (welcomeUnderline) {
    drawUnderline(ctx, welcomeTextUpper, textX, textY, welcomeFontSize, props.textColor || '#FFD700', welcomeBold)
  }

  // Draw username
  const usernameFontSize = props.usernameTextSize || 32
  const usernameBold = props.usernameTextBold || false
  const usernameItalic = props.usernameTextItalic || false
  const usernameUnderline = props.usernameTextUnderline || false

  ctx.font = buildFontString(usernameFontSize, props.fontFamily || 'arial', usernameBold, usernameItalic)
  const usernameY = textY + welcomeFontSize + 10

  const usernameTextUpper = usernameText.value.toUpperCase()

  ctx.fillStyle = '#000000'
  ctx.fillText(usernameTextUpper, textX + 2, usernameY + 2)

  ctx.fillStyle = '#ffffff'
  ctx.fillText(usernameTextUpper, textX, usernameY)

  // Draw underline if enabled
  if (usernameUnderline) {
    drawUnderline(ctx, usernameTextUpper, textX, usernameY, usernameFontSize, '#ffffff', usernameBold)
  }

  // Update element bounds
  elementBounds.value = {
    avatar: { x: avatarX, y: avatarY, width: totalAvatarSize, height: totalAvatarSize },
    welcomeText: { x: textX, y: textY, width: 0, height: 0 }
  }

  // Draw shaped avatar border (only if enabled)
  if (borderEnabled) {
    drawAvatarShapeBorder(ctx, avatarX, avatarY, totalAvatarSize, borderWidth)
  }

  // Draw shaped avatar inner
  drawAvatarShapeInner(ctx, avatarX + borderWidth, avatarY + borderWidth, avatarSize)

  // Avatar silhouette (centered on the shape)
  ctx.fillStyle = '#ffffff'
  const centerX = avatarX + totalAvatarSize / 2
  const centerY = avatarY + totalAvatarSize / 2

  ctx.beginPath()
  ctx.arc(centerX, centerY - 15, 25, 0, Math.PI * 2)
  ctx.fill()

  ctx.beginPath()
  ctx.arc(centerX, centerY + 30, 35, Math.PI, 0)
  ctx.fill()
}

const getCanvasCoordinates = (event) => {
  const canvas = canvasRef.value
  const rect = canvas.getBoundingClientRect()
  const scaleX = canvas.width / rect.width
  const scaleY = canvas.height / rect.height
  return {
    x: (event.clientX - rect.left) * scaleX,
    y: (event.clientY - rect.top) * scaleY
  }
}

const isPointInCircle = (point, centerX, centerY, radius) => {
  const dx = point.x - centerX
  const dy = point.y - centerY
  return dx * dx + dy * dy <= radius * radius
}

const isPointInRect = (point, x, y, width, height) => {
  return point.x >= x && point.x <= x + width && point.y >= y && point.y <= y + height
}

const handleMouseDown = (event) => {
  const canvas = canvasRef.value
  if (!canvas) return

  const pos = getCanvasCoordinates(event)
  const bounds = elementBounds.value

  // Check if clicking on avatar (with larger hit area)
  const avatarCenterX = bounds.avatar.x + bounds.avatar.width / 2
  const avatarCenterY = bounds.avatar.y + bounds.avatar.height / 2
  const hitRadius = Math.max(bounds.avatar.width, bounds.avatar.height) / 2 + 10

  if (isPointInCircle(pos, avatarCenterX, avatarCenterY, hitRadius)) {
    isDragging.value = true
    dragTarget.value = 'avatar'
    dragStartPos.value = pos
    elementStartPos.value = { x: currentAvatarX.value, y: currentAvatarY.value }
    canvas.style.cursor = 'grabbing'
    return
  }

  // Check if clicking on text area (both welcome text and username)
  const textArea = {
    x: bounds.welcomeText.x - 200,
    y: bounds.welcomeText.y - 10,
    width: 400,
    height: 100
  }

  if (isPointInRect(pos, textArea.x, textArea.y, textArea.width, textArea.height)) {
    isDragging.value = true
    dragTarget.value = 'text'
    dragStartPos.value = pos
    elementStartPos.value = { x: textOffsetX.value, y: textOffsetY.value }
    canvas.style.cursor = 'grabbing'
  }
}

const handleMouseMove = (event) => {
  const canvas = canvasRef.value
  if (!canvas) return

  if (!isDragging.value) {
    // Update cursor on hover
    const pos = getCanvasCoordinates(event)
    const bounds = elementBounds.value

    // Check avatar hover
    const avatarCenterX = bounds.avatar.x + bounds.avatar.width / 2
    const avatarCenterY = bounds.avatar.y + bounds.avatar.height / 2
    const hitRadius = Math.max(bounds.avatar.width, bounds.avatar.height) / 2 + 10

    if (isPointInCircle(pos, avatarCenterX, avatarCenterY, hitRadius)) {
      canvas.style.cursor = 'grab'
      return
    }

    // Check text hover
    const textArea = {
      x: bounds.welcomeText.x - 200,
      y: bounds.welcomeText.y - 10,
      width: 400,
      height: 100
    }

    if (isPointInRect(pos, textArea.x, textArea.y, textArea.width, textArea.height)) {
      canvas.style.cursor = 'grab'
      return
    }

    canvas.style.cursor = 'default'
    return
  }

  const pos = getCanvasCoordinates(event)
  const dx = pos.x - dragStartPos.value.x
  const dy = pos.y - dragStartPos.value.y

  // Snap-to-grid function (snap to nearest 25px grid)
  const GRID_SIZE = 25
  const snapToGrid = (value) => {
    const snapped = Math.round(value / GRID_SIZE) * GRID_SIZE
    return snapped
  }

  // Check if value is exactly on a grid line (for smart guides)
  const isOnGridLine = (value) => {
    return Math.abs(value - Math.round(value / GRID_SIZE) * GRID_SIZE) < 1
  }

  if (dragTarget.value === 'avatar') {
    currentAvatarX.value = elementStartPos.value.x + dx
    currentAvatarY.value = elementStartPos.value.y + dy
    // Apply snap to grid
    const snappedX = snapToGrid(currentAvatarX.value)
    const snappedY = snapToGrid(currentAvatarY.value)
    // Update parent with snapped values
    emit('update:avatarOffsetX', snappedX)
    emit('update:avatarOffsetY', snappedY)
    // Update display with snapped values for visual feedback
    currentAvatarX.value = snappedX
    currentAvatarY.value = snappedY
    // Update smart guides for avatar
    smartGuides.value.avatar.verticalX = isOnGridLine(snappedX) ? snappedX : null
    smartGuides.value.avatar.horizontalY = isOnGridLine(snappedY) ? snappedY : null
    // Reset text guides when dragging avatar
    smartGuides.value.text.verticalX = null
    smartGuides.value.text.horizontalY = null
  } else if (dragTarget.value === 'text') {
    textOffsetX.value = elementStartPos.value.x + dx
    textOffsetY.value = elementStartPos.value.y + dy
    // Apply snap to grid
    const snappedX = snapToGrid(textOffsetX.value)
    const snappedY = snapToGrid(textOffsetY.value)
    // Update parent with snapped values
    emit('update:textOffsetX', snappedX)
    emit('update:textOffsetY', snappedY)
    textOffsetX.value = snappedX
    textOffsetY.value = snappedY
    // Update smart guides for text
    smartGuides.value.text.verticalX = isOnGridLine(snappedX) ? snappedX : null
    smartGuides.value.text.horizontalY = isOnGridLine(snappedY) ? snappedY : null
    // Reset avatar guides when dragging text
    smartGuides.value.avatar.verticalX = null
    smartGuides.value.avatar.horizontalY = null
  }

  // Use RAF for smooth drag rendering (no flicker)
  if (dragAnimationId) {
    cancelAnimationFrame(dragAnimationId)
  }
  dragAnimationId = requestAnimationFrame(() => {
    renderDragPreview()
    dragAnimationId = null
  })
}

const handleMouseUp = () => {
  if (isDragging.value) {
    isDragging.value = false
    dragTarget.value = null
    // Cancel any pending drag render
    if (dragAnimationId) {
      cancelAnimationFrame(dragAnimationId)
      dragAnimationId = null
    }
    // Clear smart guides when dragging stops
    smartGuides.value.avatar.verticalX = null
    smartGuides.value.avatar.horizontalY = null
    smartGuides.value.text.verticalX = null
    smartGuides.value.text.horizontalY = null
    if (canvasRef.value) {
      canvasRef.value.style.cursor = 'default'
    }
    // Full render to finalize state (ensures cache is built if needed)
    generatePreview()
  }
}

const handleMouseLeave = () => {
  if (isDragging.value) {
    // Cancel any pending drag render
    if (dragAnimationId) {
      cancelAnimationFrame(dragAnimationId)
      dragAnimationId = null
    }
    // Clear smart guides when mouse leaves
    smartGuides.value.avatar.verticalX = null
    smartGuides.value.avatar.horizontalY = null
    smartGuides.value.text.verticalX = null
    smartGuides.value.text.horizontalY = null
    handleMouseUp()
  }
}

const generatePreview = async () => {
  if (!canvasRef.value) return

  isGenerating.value = true
  previewError.value = false

  try {
    const canvas = canvasRef.value
    const ctx = canvas.getContext('2d')

    // Set canvas size (no border)
    const CANVAS_WIDTH = 1000
    const CANVAS_HEIGHT = 400
    canvas.width = CANVAS_WIDTH
    canvas.height = CANVAS_HEIGHT

    // Check if cache needs rebuilding
    const needsCacheRebuild = !isCacheValid.value ||
      cachedBannerUrl.value !== props.bannerUrl ||
      cachedShowGrid.value !== showGrid.value

    // Build or rebuild background cache
    if (needsCacheRebuild) {
      await buildBackgroundCache()
    }

    // Copy cached background to main canvas
    if (offscreenCanvas.value && isCacheValid.value) {
      ctx.drawImage(offscreenCanvas.value, 0, 0)
    } else {
      // Fallback: fill with background color
      ctx.fillStyle = '#2b2d31'
      ctx.fillRect(0, 0, canvas.width, canvas.height)
    }

    // Get font family
    const fontFamily = getFontFamily(props.fontFamily || 'arial')

    // Draw avatar placeholder (use dynamic size from props)
    const avatarSize = props.avatarSize || 180
    const borderEnabled = props.avatarBorderEnabled !== undefined ? props.avatarBorderEnabled : true
    const borderWidth = borderEnabled ? (props.avatarBorderWidth || 6) : 0
    const totalAvatarSize = avatarSize + borderWidth * 2

    // Calculate avatar position (matching bot's get_avatar_position logic + manual offset)
    let avatarX, avatarY
    const position = props.profilePosition || 'center'

    if (position === 'center') {
      avatarX = (CANVAS_WIDTH - totalAvatarSize) / 2
      avatarY = (CANVAS_HEIGHT - totalAvatarSize) / 2 - 40  // Offset up for text
    } else if (position === 'left') {
      avatarX = 30
      avatarY = (CANVAS_HEIGHT - totalAvatarSize) / 2 - 40
    } else if (position === 'right') {
      avatarX = CANVAS_WIDTH - totalAvatarSize - 30
      avatarY = (CANVAS_HEIGHT - totalAvatarSize) / 2 - 40
    } else {
      // Default to center
      avatarX = (CANVAS_WIDTH - totalAvatarSize) / 2
      avatarY = (CANVAS_HEIGHT - totalAvatarSize) / 2 - 40
    }

    // Apply manual offset (use local drag value if dragging, otherwise use prop)
    if (dragTarget.value === 'avatar' || (currentAvatarX.value !== 0 && !isDragging.value)) {
      avatarX += currentAvatarX.value
      avatarY += currentAvatarY.value
    } else {
      avatarX += (props.avatarOffsetX || 0)
      avatarY += (props.avatarOffsetY || 0)
      // Sync local state with props
      currentAvatarX.value = props.avatarOffsetX || 0
      currentAvatarY.value = props.avatarOffsetY || 0
    }

    // Draw text (independent position, not tied to avatar)
    // Base position for text
    const BASE_TEXT_Y = 120  // Fixed base Y position for text
    const BASE_TEXT_X = CANVAS_WIDTH / 2  // Center horizontally

    // Sync text offset with props when not dragging
    if (dragTarget.value !== 'text') {
      textOffsetX.value = props.textOffsetX || 0
      textOffsetY.value = props.textOffsetY || 0
    }

    let textX = BASE_TEXT_X + textOffsetX.value
    let textY = BASE_TEXT_Y + textOffsetY.value

    // Draw grid overlay (for positioning reference)
    if (showGrid.value) {
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.15)'
      ctx.lineWidth = 1

      // Vertical lines every 50px
      for (let x = 0; x <= CANVAS_WIDTH; x += 50) {
        ctx.beginPath()
        ctx.moveTo(x, 0)
        ctx.lineTo(x, CANVAS_HEIGHT)
        ctx.stroke()
      }

      // Horizontal lines every 50px
      for (let y = 0; y <= CANVAS_HEIGHT; y += 50) {
        ctx.beginPath()
        ctx.moveTo(0, y)
        ctx.lineTo(CANVAS_WIDTH, y)
        ctx.stroke()
      }

      // Center lines
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)'
      ctx.beginPath()
      ctx.moveTo(CANVAS_WIDTH / 2, 0)
      ctx.lineTo(CANVAS_WIDTH / 2, CANVAS_HEIGHT)
      ctx.stroke()
      ctx.beginPath()
      ctx.moveTo(0, CANVAS_HEIGHT / 2)
      ctx.lineTo(CANVAS_WIDTH, CANVAS_HEIGHT / 2)
      ctx.stroke()
    }

    // Draw smart guides (snap indicators) - only show while dragging
    if (isDragging.value) {
      ctx.strokeStyle = '#00D9FF'  // Cyan color for smart guides
      ctx.lineWidth = 2
      ctx.setLineDash([8, 4])  // Dashed line for guides

      // Avatar smart guides
      const avatarCenterX = avatarX + totalAvatarSize / 2
      const avatarCenterY = avatarY + totalAvatarSize / 2

      // Vertical guide for avatar (extends from element center)
      if (smartGuides.value.avatar.verticalX !== null) {
        ctx.beginPath()
        ctx.moveTo(avatarCenterX, 0)
        ctx.lineTo(avatarCenterX, CANVAS_HEIGHT)
        ctx.stroke()

        // Draw snap indicator at intersection with element
        ctx.fillStyle = '#00D9FF'
        ctx.beginPath()
        ctx.arc(avatarCenterX, avatarCenterY, 5, 0, Math.PI * 2)
        ctx.fill()
      }

      // Horizontal guide for avatar
      if (smartGuides.value.avatar.horizontalY !== null) {
        ctx.beginPath()
        ctx.moveTo(0, avatarCenterY)
        ctx.lineTo(CANVAS_WIDTH, avatarCenterY)
        ctx.stroke()

        // Draw snap indicator at intersection with element
        ctx.fillStyle = '#00D9FF'
        ctx.beginPath()
        ctx.arc(avatarCenterX, avatarCenterY, 5, 0, Math.PI * 2)
        ctx.fill()
      }

      // Text smart guides (center is at textX, textY + 30 approximately)
      const textCenterX = textX
      const textCenterY = textY + 30  // Approximate center of welcome text

      // Vertical guide for text
      if (smartGuides.value.text.verticalX !== null) {
        ctx.beginPath()
        ctx.moveTo(textCenterX, 0)
        ctx.lineTo(textCenterX, CANVAS_HEIGHT)
        ctx.stroke()

        // Draw snap indicator
        ctx.fillStyle = '#00D9FF'
        ctx.beginPath()
        ctx.arc(textCenterX, textCenterY, 5, 0, Math.PI * 2)
        ctx.fill()
      }

      // Horizontal guide for text
      if (smartGuides.value.text.horizontalY !== null) {
        ctx.beginPath()
        ctx.moveTo(0, textCenterY)
        ctx.lineTo(CANVAS_WIDTH, textCenterY)
        ctx.stroke()

        // Draw snap indicator
        ctx.fillStyle = '#00D9FF'
        ctx.beginPath()
        ctx.arc(textCenterX, textCenterY, 5, 0, Math.PI * 2)
        ctx.fill()
      }

      // Reset line dash
      ctx.setLineDash([])
    }

    // Draw welcome text with shadow
    const welcomeFontSize = props.welcomeTextSize || 56
    const welcomeBold = props.welcomeTextBold || false
    const welcomeItalic = props.welcomeTextItalic || false
    const welcomeUnderline = props.welcomeTextUnderline || false

    ctx.font = buildFontString(welcomeFontSize, props.fontFamily || 'arial', welcomeBold, welcomeItalic)
    ctx.textAlign = 'center'
    ctx.textBaseline = 'top'

    const welcomeTextUpper = (props.welcomeText || 'WELCOME').toUpperCase()

    // Shadow
    ctx.fillStyle = '#000000'
    ctx.fillText(welcomeTextUpper, textX + 3, textY + 3)

    // Main text
    ctx.fillStyle = props.textColor || '#FFD700'
    ctx.fillText(welcomeTextUpper, textX, textY)

    // Draw underline if enabled
    if (welcomeUnderline) {
      drawUnderline(ctx, welcomeTextUpper, textX, textY, welcomeFontSize, props.textColor || '#FFD700', welcomeBold)
    }

    // Draw username with shadow (using editable username text)
    const usernameFontSize = props.usernameTextSize || 32
    const usernameBold = props.usernameTextBold || false
    const usernameItalic = props.usernameTextItalic || false
    const usernameUnderline = props.usernameTextUnderline || false

    ctx.font = buildFontString(usernameFontSize, props.fontFamily || 'arial', usernameBold, usernameItalic)
    const usernameY = textY + welcomeFontSize + 10

    const usernameTextUpper = usernameText.value.toUpperCase()

    // Shadow
    ctx.fillStyle = '#000000'
    ctx.fillText(usernameTextUpper, textX + 2, usernameY + 2)

    // Main text
    ctx.fillStyle = '#ffffff'
    ctx.fillText(usernameTextUpper, textX, usernameY)

    // Draw underline if enabled
    if (usernameUnderline) {
      drawUnderline(ctx, usernameTextUpper, textX, usernameY, usernameFontSize, '#ffffff', usernameBold)
    }

    // Store element bounds for hit detection (do this before drawing avatar on top)
    elementBounds.value = {
      avatar: { x: avatarX, y: avatarY, width: totalAvatarSize, height: totalAvatarSize },
      welcomeText: { x: textX, y: textY, width: 0, height: 0 } // Position updated
    }

    // Draw shaped avatar border (only if enabled)
    if (borderEnabled) {
      drawAvatarShapeBorder(ctx, avatarX, avatarY, totalAvatarSize, borderWidth)
    }

    // Draw shaped avatar inner
    drawAvatarShapeInner(ctx, avatarX + borderWidth, avatarY + borderWidth, avatarSize)

    // Avatar silhouette
    ctx.fillStyle = '#ffffff'
    const centerX = avatarX + totalAvatarSize / 2
    const centerY = avatarY + totalAvatarSize / 2

    // Head
    ctx.beginPath()
    ctx.arc(centerX, centerY - 15, 25, 0, Math.PI * 2)
    ctx.fill()

    // Body (shoulders)
    ctx.beginPath()
    ctx.arc(centerX, centerY + 30, 35, Math.PI, 0)
    ctx.fill()

  } catch (e) {
    console.error('Preview generation failed:', e)
    previewError.value = true
  } finally {
    isGenerating.value = false
  }
}

onMounted(() => {
  generatePreview()
  // Set up event listeners for drag functionality
  const canvas = canvasRef.value
  if (canvas) {
    canvas.addEventListener('mousedown', handleMouseDown)
    canvas.addEventListener('mousemove', handleMouseMove)
    canvas.addEventListener('mouseup', handleMouseUp)
    canvas.addEventListener('mouseleave', handleMouseLeave)
  }
})

onUnmounted(() => {
  cleanup()
})

// Watch all props and regenerate preview when any changes - use watchEffect for deep reactivity
watchEffect(() => {
  // Access all props to track them (including size props, shape, and text styles)
  const {
    bannerUrl, welcomeText, text, textColor, profilePosition, fontFamily,
    avatarOffsetX, avatarOffsetY, textOffsetX, textOffsetY,
    welcomeTextSize, usernameTextSize, avatarSize, avatarShape,
    welcomeTextBold, welcomeTextItalic, welcomeTextUnderline,
    usernameTextBold, usernameTextItalic, usernameTextUnderline,
    avatarBorderEnabled, avatarBorderWidth
  } = props

  // Load GIF frames if banner URL is a GIF
  if (bannerUrl) {
    loadGifFrames(bannerUrl)
  }

  // Only regenerate canvas preview when NOT in animated preview mode
  if (!showAnimatedPreview.value) {
    // Small delay to avoid too many regenerates during typing
    const timer = setTimeout(() => {
      generatePreview()
    }, 100)

    return () => clearTimeout(timer)
  }
})

// Watch for preview mode changes
watch(showAnimatedPreview, (newValue) => {
  if (newValue) {
    // Switching to live preview - start animation after canvas is mounted
    const startAnimation = () => {
      if (liveCanvasRef.value && liveImageRef.value) {
        console.log('Starting live preview with overlay')
        animateLivePreview()
      } else {
        // Retry after a short delay
        setTimeout(startAnimation, 50)
      }
    }
    // Wait for Vue to render the canvas
    nextTick(() => {
      setTimeout(startAnimation, 100)
    })
  } else {
    // Switching back to edit mode - stop animation and regenerate canvas
    if (overlayRenderInterval) {
      cancelAnimationFrame(overlayRenderInterval)
      overlayRenderInterval = null
    }
    // Ensure edit mode canvas has event listeners
    nextTick(() => {
      const canvas = canvasRef.value
      if (canvas) {
        // Remove existing listeners to avoid duplicates
        canvas.removeEventListener('mousedown', handleMouseDown)
        canvas.removeEventListener('mousemove', handleMouseMove)
        canvas.removeEventListener('mouseup', handleMouseUp)
        canvas.removeEventListener('mouseleave', handleMouseLeave)
        // Add listeners
        canvas.addEventListener('mousedown', handleMouseDown)
        canvas.addEventListener('mousemove', handleMouseMove)
        canvas.addEventListener('mouseup', handleMouseUp)
        canvas.addEventListener('mouseleave', handleMouseLeave)
      }
      setTimeout(() => {
        generatePreview()
      }, 50)
    })
  }
})

// Watch showGrid changes to invalidate cache
watch(showGrid, () => {
  isCacheValid.value = false
})

async function refreshPreview() {
  await generatePreview()
}

function resetPosition() {
  // Default positions: avatar (0, -25), text (0, 125)
  currentAvatarX.value = 0
  currentAvatarY.value = -25
  textOffsetX.value = 0
  textOffsetY.value = 125
  emit('update:avatarOffsetX', 0)
  emit('update:avatarOffsetY', -25)
  emit('update:textOffsetX', 0)
  emit('update:textOffsetY', 125)
  generatePreview()
}
</script>

<template>
  <div class="preview-container">
    <div class="preview-header">
      <h3 class="preview-title">Preview</h3>
      <div class="header-buttons">
        <button @click="resetPosition" class="reset-btn" title="Reset position to center">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74-2.74L3 8"/>
            <path d="M3 3v5h5"/>
          </svg>
        </button>
        <button @click="refreshPreview" class="refresh-btn" :disabled="isGenerating">
          <svg v-if="!isGenerating" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M23 4v6h-6M1 20v-6h6"/>
            <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
          </svg>
          <svg v-else class="spin" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
          </svg>
        </button>
      </div>
    </div>

    <!-- Preview Controls -->
    <div class="preview-controls">
      <label class="control-item">
        <input type="checkbox" v-model="showGrid" @change="generatePreview" />
        <span>Show Grid (Snap: 25px)</span>
      </label>
      <label class="control-item">
        <span>Preview Username:</span>
        <input
          type="text"
          v-model="usernameText"
          @input="generatePreview"
          class="username-input"
          maxlength="20"
        />
      </label>

      <!-- GIF Controls -->
      <template v-if="isGif && gifLoaded">
        <div class="gif-indicator">
          <span class="gif-badge">GIF</span>
        </div>
        <button
          @click="showAnimatedPreview = !showAnimatedPreview"
          class="preview-toggle-btn"
          :class="{ active: showAnimatedPreview }"
        >
          <svg v-if="!showAnimatedPreview" xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polygon points="5 3 19 12 5 21 5 3"/>
          </svg>
          <svg v-else xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="6" y="4" width="4" height="16"/>
            <rect x="14" y="4" width="4" height="16"/>
          </svg>
          <span>{{ showAnimatedPreview ? 'Edit Mode' : 'Live Preview' }}</span>
        </button>
      </template>
    </div>

    <!-- Live Preview - Native GIF + Canvas Overlay -->
    <div v-if="isGif && gifLoaded && showAnimatedPreview" class="preview-canvas-wrapper live-preview-wrapper">
      <!-- Native GIF image for smooth animation -->
      <img
        ref="liveImageRef"
        :src="bannerUrl"
        alt="GIF Preview"
        class="live-gif-image"
      />
      <!-- Canvas overlay for avatar and text -->
      <canvas
        ref="liveCanvasRef"
        width="1000"
        height="400"
        class="preview-canvas overlay-canvas"
      ></canvas>
      <div v-if="isLivePreviewLoading" class="preview-loading-overlay">
        <div class="loading-spinner"></div>
        <p>Loading...</p>
      </div>
    </div>

    <!-- Canvas Preview (for editing with overlays) -->
    <div v-show="!(isGif && gifLoaded && showAnimatedPreview)" class="preview-canvas-wrapper">
      <canvas
        v-if="!previewError"
        ref="canvasRef"
        width="1000"
        height="400"
        class="preview-canvas"
      ></canvas>
      <div v-else class="preview-error">
        <p>Failed to load banner image</p>
        <p class="text-sm text-gray-400">{{ bannerUrl }}</p>
      </div>
    </div>

    <p class="preview-note">
      <template v-if="isGif && showAnimatedPreview">
        <svg class="inline-icon" xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18"/>
          <line x1="7" y1="2" x2="7" y2="22"/>
          <line x1="17" y1="2" x2="17" y2="22"/>
          <line x1="2" y1="12" x2="22" y2="12"/>
          <line x1="2" y1="7" x2="7" y2="7"/>
          <line x1="2" y1="17" x2="7" y2="17"/>
          <line x1="17" y1="17" x2="22" y2="17"/>
          <line x1="17" y1="7" x2="22" y2="7"/>
        </svg>
        Live preview with avatar and text overlay. Click "Edit Mode" button to switch back to editing.
      </template>
      <template v-else-if="isGif">
        <svg class="inline-icon" xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>
        </svg>
        Drag avatar or text to reposition. Auto-snaps to 25px grid with cyan smart guides showing alignment. Click "Live Preview" to see animation with overlays.
      </template>
      <template v-else>
        <svg class="inline-icon" xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>
        </svg>
        Drag avatar or text to reposition. Auto-snaps to 25px grid with cyan smart guides showing alignment.
      </template>
    </p>
  </div>
</template>

<style scoped>
.preview-container {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.preview-title {
  font-size: 1rem;
  font-weight: 600;
  color: #dbdee1;
}

.header-buttons {
  display: flex;
  gap: 0.5rem;
}

.reset-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0.375rem 0.5rem;
  background: #404249;
  border: none;
  border-radius: 0.25rem;
  color: #dbdee1;
  cursor: pointer;
  transition: background 0.15s ease;
}

.reset-btn:hover {
  background: #4e5058;
}

.reset-btn svg {
  width: 14px;
  height: 14px;
}

.refresh-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0.375rem 0.75rem;
  background: #5865f2;
  border: none;
  border-radius: 0.25rem;
  color: white;
  cursor: pointer;
  transition: background 0.15s ease;
}

.refresh-btn:hover:not(:disabled) {
  background: #4752c4;
}

.refresh-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.preview-controls {
  display: flex;
  gap: 1rem;
  align-items: center;
  flex-wrap: wrap;
  padding: 0.5rem;
  background: #1e1f22;
  border-radius: 0.25rem;
}

.control-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  color: #dbdee1;
  cursor: pointer;
}

.control-item input[type="checkbox"] {
  cursor: pointer;
}

.username-input {
  padding: 0.25rem 0.5rem;
  background: #383a40;
  border: 1px solid #4e5058;
  border-radius: 0.25rem;
  color: #dbdee1;
  font-size: 0.875rem;
  width: 150px;
}

.username-input:focus {
  outline: none;
  border-color: #5865f2;
}

.gif-indicator {
  display: flex;
  align-items: center;
}

.gif-badge {
  padding: 0.125rem 0.5rem;
  background: linear-gradient(135deg, #5865f2, #eb459e);
  border-radius: 0.25rem;
  font-size: 0.625rem;
  font-weight: 700;
  color: white;
  letter-spacing: 0.05em;
}

.gif-controls {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  margin-left: auto;
}

.frame-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0.25rem;
  background: #383a40;
  border: 1px solid #4e5058;
  border-radius: 0.25rem;
  color: #dbdee1;
  cursor: pointer;
  transition: background 0.15s ease;
}

.frame-btn:hover {
  background: #4e5058;
}

.frame-btn svg {
  width: 14px;
  height: 14px;
}

.play-btn {
  background: #5865f2;
  border-color: #5865f2;
}

.play-btn:hover {
  background: #4752c4;
}

.frame-counter {
  font-size: 0.75rem;
  color: #80848e;
  margin-left: 0.5rem;
  min-width: 50px;
  text-align: center;
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.preview-canvas-wrapper {
  background: #1e1f22;
  border-radius: 0.5rem;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

.preview-canvas {
  max-width: 100%;
  height: auto;
  display: block;
  cursor: default;
  user-select: none;
}

.preview-error {
  padding: 2rem;
  text-align: center;
  color: #dbdee1;
}

.preview-note {
  font-size: 0.75rem;
  color: #80848e;
  text-align: center;
}

.preview-toggle-btn {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.375rem 0.75rem;
  background: #383a40;
  border: 1px solid #5865f2;
  border-radius: 0.25rem;
  color: #dbdee1;
  font-size: 0.875rem;
  cursor: pointer;
  transition: background 0.15s ease;
}

.preview-toggle-btn:hover {
  background: #4e5058;
}

.preview-toggle-btn.active {
  background: #5865f2;
}

.preview-toggle-btn svg {
  width: 14px;
  height: 14px;
}

.animated-gif-preview {
  max-width: 100%;
  height: auto;
  display: block;
  margin: 0 auto;
}

.preview-loading {
  padding: 2rem;
  text-align: center;
  color: #dbdee1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #383a40;
  border-top-color: #5865f2;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.preview-canvas-wrapper {
  background: #1e1f22;
  border-radius: 0.5rem;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Live preview wrapper - positions GIF and overlay */
.live-preview-wrapper {
  position: relative;
  width: 1000px;
  height: 400px;
}

.live-gif-image {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: cover; /* Crop to fit like edit mode */
}

.overlay-canvas {
  position: absolute;
  top: 0;
  left: 0;
  pointer-events: none; /* Let clicks pass through to the GIF */
}

.preview-loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  background: rgba(30, 31, 34, 0.8);
  z-index: 10;
}

.inline-icon {
  display: inline-block;
  vertical-align: middle;
  margin-right: 0.25rem;
  margin-top: -2px;
}
</style>
