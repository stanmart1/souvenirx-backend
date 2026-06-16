"""Logo processing service for image optimization, background removal, and overlay rendering"""

import io
import uuid
from typing import Optional, Tuple
from PIL import Image, ImageFilter, ImageEnhance, ImageDraw
import colorgram
import httpx
from rembg import remove
import numpy as np

from app.models.logo_upload import LogoOverlayConfig


class LogoProcessingService:
    """Service for processing uploaded logos and generating previews"""
    
    # Configuration
    THUMBNAIL_SIZE = (200, 200)
    OPTIMIZED_MAX_SIZE = (1000, 1000)
    ALLOWED_FORMATS = {'PNG', 'JPEG', 'JPG', 'WEBP', 'SVG'}
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    
    @staticmethod
    async def process_logo_upload(
        file_content: bytes,
        filename: str,
        mime_type: str,
    ) -> dict:
        """
        Process an uploaded logo file.
        
        Args:
            file_content: Raw file bytes
            filename: Original filename
            mime_type: MIME type of the file
            
        Returns:
            dict with processed file URLs and metadata
            
        Raises:
            ValueError: If file is invalid or too large
        """
        # Validate file size
        if len(file_content) > LogoProcessingService.MAX_FILE_SIZE:
            raise ValueError(f"File size exceeds {LogoProcessingService.MAX_FILE_SIZE / 1024 / 1024}MB limit")
        
        # Determine if it's a vector file
        is_vector = mime_type == 'image/svg+xml'
        
        if is_vector:
            # For SVG, we don't process the image, just store it
            return {
                "file_content": file_content,
                "thumbnail_content": None,
                "optimized_content": None,
                "transparent_content": None,
                "width": 0,  # SVG is scalable
                "height": 0,
                "aspect_ratio": 1.0,
                "has_transparency": True,
                "dominant_colors": [],
                "is_vector": True,
            }
        
        # Open image
        try:
            image = Image.open(io.BytesIO(file_content))
        except Exception as e:
            raise ValueError(f"Invalid image file: {str(e)}")
        
        # Convert RGBA to RGB if no transparency
        if image.mode == 'RGBA':
            # Check if image actually has transparency
            alpha = image.split()[3]
            if alpha.getextrema() == (255, 255):
                # No transparency, convert to RGB
                background = Image.new('RGB', image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[3])
                image = background
                has_transparency = False
            else:
                has_transparency = True
        elif image.mode == 'LA':
            has_transparency = True
        elif image.mode == 'P' and 'transparency' in image.info:
            has_transparency = True
        else:
            has_transparency = False
            if image.mode != 'RGB':
                image = image.convert('RGB')
        
        # Get metadata
        width, height = image.size
        aspect_ratio = width / height
        
        # Generate thumbnail (200x200)
        thumbnail = image.copy()
        thumbnail.thumbnail(LogoProcessingService.THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
        thumbnail_bytes = io.BytesIO()
        thumbnail.save(thumbnail_bytes, format='PNG', optimize=True)
        thumbnail_content = thumbnail_bytes.getvalue()
        
        # Generate optimized version (max 1000x1000)
        optimized = image.copy()
        optimized.thumbnail(LogoProcessingService.OPTIMIZED_MAX_SIZE, Image.Resampling.LANCZOS)
        optimized_bytes = io.BytesIO()
        optimized.save(optimized_bytes, format='PNG', optimize=True)
        optimized_content = optimized_bytes.getvalue()
        
        # Remove background (if not transparent)
        transparent_content = None
        if not has_transparency:
            try:
                # Use rembg to remove background
                transparent_bytes = remove(file_content)
                transparent_content = transparent_bytes
            except Exception as e:
                print(f"Background removal failed: {e}")
                # Continue without transparent version
        
        # Extract dominant colors
        try:
            colors = colorgram.extract(io.BytesIO(file_content), 5)
            dominant_colors = [
                f"#{color.rgb.r:02x}{color.rgb.g:02x}{color.rgb.b:02x}"
                for color in colors
            ]
        except Exception as e:
            print(f"Color extraction failed: {e}")
            dominant_colors = []
        
        return {
            "file_content": file_content,
            "thumbnail_content": thumbnail_content,
            "optimized_content": optimized_content,
            "transparent_content": transparent_content,
            "width": width,
            "height": height,
            "aspect_ratio": aspect_ratio,
            "has_transparency": has_transparency,
            "dominant_colors": dominant_colors,
            "is_vector": False,
        }
    
    @staticmethod
    async def apply_logo_overlay(
        product_mockup_url: str,
        logo_url: str,
        overlay_config: LogoOverlayConfig,
        design_area: dict,
    ) -> bytes:
        """
        Apply logo overlay to product mockup.
        
        Args:
            product_mockup_url: URL of the product mockup image
            logo_url: URL of the logo image
            overlay_config: Configuration for logo positioning and effects
            design_area: Design area definition from mockup template
            
        Returns:
            bytes: Preview image as JPEG bytes
        """
        # Download images
        async with httpx.AsyncClient() as client:
            mockup_response = await client.get(product_mockup_url)
            mockup_image = Image.open(io.BytesIO(mockup_response.content))
            
            logo_response = await client.get(logo_url)
            logo_image = Image.open(io.BytesIO(logo_response.content))
        
        # Convert to RGBA for transparency support
        mockup_image = mockup_image.convert('RGBA')
        logo_image = logo_image.convert('RGBA')
        
        # Apply effects to logo
        logo_image = await LogoProcessingService._apply_effects(
            logo_image,
            overlay_config
        )
        
        # Calculate position and size
        design_x = design_area['x']
        design_y = design_area['y']
        design_width = design_area['width']
        design_height = design_area['height']
        
        # Calculate logo size based on scale
        logo_width = int(design_width * overlay_config.scale)
        
        # Maintain aspect ratio if locked
        if overlay_config.lock_aspect_ratio:
            logo_height = int(logo_width / (logo_image.width / logo_image.height))
        else:
            logo_height = int(design_height * overlay_config.scale)
        
        # Resize logo
        logo_image = logo_image.resize(
            (logo_width, logo_height),
            Image.Resampling.LANCZOS
        )
        
        # Rotate logo
        if overlay_config.rotation != 0:
            logo_image = logo_image.rotate(
                overlay_config.rotation,
                expand=True,
                fillcolor=(0, 0, 0, 0),
                resample=Image.Resampling.BICUBIC
            )
        
        # Calculate paste position (relative to design area)
        paste_x = int(design_x + (design_width * overlay_config.position_x) - (logo_image.width / 2))
        paste_y = int(design_y + (design_height * overlay_config.position_y) - (logo_image.height / 2))
        
        # Apply perspective transform if needed
        if 'perspective' in design_area:
            logo_image = await LogoProcessingService._apply_perspective(
                logo_image,
                design_area['perspective']
            )
        
        # Paste logo onto mockup
        mockup_image.paste(logo_image, (paste_x, paste_y), logo_image)
        
        # Convert to RGB for JPEG output
        final_image = mockup_image.convert('RGB')
        
        # Save to bytes
        output = io.BytesIO()
        final_image.save(output, format='JPEG', quality=90, optimize=True)
        
        return output.getvalue()
    
    @staticmethod
    async def _apply_effects(
        image: Image.Image,
        config: LogoOverlayConfig
    ) -> Image.Image:
        """
        Apply effects to logo image.
        
        Args:
            image: PIL Image to apply effects to
            config: Overlay configuration with effect settings
            
        Returns:
            Modified PIL Image
        """
        # Flip
        if config.flip_horizontal:
            image = image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        if config.flip_vertical:
            image = image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        
        # Opacity
        if config.opacity < 1.0:
            alpha = image.split()[3] if image.mode == 'RGBA' else None
            if alpha:
                alpha = ImageEnhance.Brightness(alpha).enhance(config.opacity)
                image.putalpha(alpha)
        
        # Brightness
        if config.brightness != 1.0:
            enhancer = ImageEnhance.Brightness(image)
            image = enhancer.enhance(config.brightness)
        
        # Contrast
        if config.contrast != 1.0:
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(config.contrast)
        
        # Saturation
        if config.saturation != 1.0:
            enhancer = ImageEnhance.Color(image)
            image = enhancer.enhance(config.saturation)
        
        # Color overlay
        if config.color_overlay and config.color_overlay_opacity > 0:
            # Parse hex color
            hex_color = config.color_overlay.lstrip('#')
            r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            
            # Create color overlay
            overlay = Image.new('RGBA', image.size, (r, g, b, int(255 * config.color_overlay_opacity)))
            
            # Blend with original
            image = Image.alpha_composite(image, overlay)
        
        # Shadow
        if config.shadow_enabled:
            # Create shadow layer
            shadow = Image.new('RGBA', image.size, (0, 0, 0, 0))
            
            # Get alpha channel for shadow shape
            if image.mode == 'RGBA':
                alpha = image.split()[3]
                
                # Create shadow from alpha
                shadow_alpha = alpha.point(lambda p: int(p * 0.5))  # 50% opacity shadow
                shadow.putalpha(shadow_alpha)
                
                # Apply blur
                shadow = shadow.filter(ImageFilter.GaussianBlur(config.shadow_blur))
                
                # Create final image with shadow
                shadow_layer = Image.new('RGBA', 
                    (image.width + abs(config.shadow_offset_x) * 2,
                     image.height + abs(config.shadow_offset_y) * 2),
                    (0, 0, 0, 0)
                )
                
                # Paste shadow with offset
                shadow_x = abs(config.shadow_offset_x) + config.shadow_offset_x
                shadow_y = abs(config.shadow_offset_y) + config.shadow_offset_y
                shadow_layer.paste(shadow, (shadow_x, shadow_y))
                
                # Paste original image on top
                shadow_layer.paste(image, (abs(config.shadow_offset_x), abs(config.shadow_offset_y)), image)
                
                image = shadow_layer
        
        # Border
        if config.border_width > 0 and config.border_color:
            # Parse hex color
            hex_color = config.border_color.lstrip('#')
            r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            
            # Create new image with border
            bordered = Image.new('RGBA',
                (image.width + config.border_width * 2,
                 image.height + config.border_width * 2),
                (r, g, b, 255)
            )
            
            # Paste original image in center
            bordered.paste(image, (config.border_width, config.border_width), image)
            image = bordered
        
        return image
    
    @staticmethod
    async def _apply_perspective(
        image: Image.Image,
        perspective_points: dict
    ) -> Image.Image:
        """
        Apply perspective transformation for 3D mockups.
        
        Args:
            image: PIL Image to transform
            perspective_points: Dictionary with corner points
            
        Returns:
            Transformed PIL Image
        """
        try:
            import cv2
            
            # Convert PIL to numpy
            img_array = np.array(image)
            
            # Define source points (corners of original image)
            src_points = np.float32([
                [0, 0],
                [image.width, 0],
                [image.width, image.height],
                [0, image.height]
            ])
            
            # Define destination points (perspective corners)
            dst_points = np.float32([
                perspective_points['topLeft'],
                perspective_points['topRight'],
                perspective_points['bottomRight'],
                perspective_points['bottomLeft']
            ])
            
            # Calculate perspective transform matrix
            matrix = cv2.getPerspectiveTransform(src_points, dst_points)
            
            # Apply transformation
            result = cv2.warpPerspective(
                img_array,
                matrix,
                (image.width, image.height),
                flags=cv2.INTER_LINEAR,
                borderMode=cv2.BORDER_CONSTANT,
                borderValue=(0, 0, 0, 0)
            )
            
            # Convert back to PIL
            return Image.fromarray(result)
            
        except Exception as e:
            print(f"Perspective transformation failed: {e}")
            # Return original image if transformation fails
            return image
    
    @staticmethod
    def validate_logo_file(
        file_content: bytes,
        filename: str,
        mime_type: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate logo file before processing.
        
        Args:
            file_content: Raw file bytes
            filename: Original filename
            mime_type: MIME type
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check file size
        if len(file_content) > LogoProcessingService.MAX_FILE_SIZE:
            return False, f"File size exceeds {LogoProcessingService.MAX_FILE_SIZE / 1024 / 1024}MB limit"
        
        # Check MIME type
        allowed_mimes = {
            'image/png',
            'image/jpeg',
            'image/jpg',
            'image/webp',
            'image/svg+xml'
        }
        
        if mime_type not in allowed_mimes:
            return False, f"Invalid file type. Allowed: {', '.join(allowed_mimes)}"
        
        # Check file extension
        ext = filename.split('.')[-1].upper()
        if ext not in LogoProcessingService.ALLOWED_FORMATS:
            return False, f"Invalid file extension. Allowed: {', '.join(LogoProcessingService.ALLOWED_FORMATS)}"
        
        # Try to open image (except SVG)
        if mime_type != 'image/svg+xml':
            try:
                Image.open(io.BytesIO(file_content))
            except Exception as e:
                return False, f"Invalid image file: {str(e)}"
        
        return True, None
