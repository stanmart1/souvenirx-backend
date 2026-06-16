"""Storage service for file uploads"""

import os
import uuid
import aiofiles
from pathlib import Path
from typing import Optional
from app.config import settings


class StorageService:
    """Service for storing uploaded files"""
    
    # Storage configuration
    STORAGE_BASE_PATH = Path(settings.STORAGE_PATH if hasattr(settings, 'STORAGE_PATH') else './storage')
    STORAGE_BASE_URL = settings.STORAGE_URL if hasattr(settings, 'STORAGE_URL') else 'http://localhost:8000/storage'
    
    @staticmethod
    async def save_file(
        file_content: bytes,
        filename: str,
        subfolder: str = 'uploads'
    ) -> str:
        """
        Save file to storage.
        
        Args:
            file_content: File bytes to save
            filename: Original filename
            subfolder: Subfolder within storage (e.g., 'logos', 'mockups')
            
        Returns:
            str: Public URL of the saved file
        """
        # Generate unique filename
        ext = filename.split('.')[-1] if '.' in filename else 'bin'
        unique_filename = f"{uuid.uuid4()}.{ext}"
        
        # Create full path
        folder_path = StorageService.STORAGE_BASE_PATH / subfolder
        folder_path.mkdir(parents=True, exist_ok=True)
        
        file_path = folder_path / unique_filename
        
        # Save file
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(file_content)
        
        # Return public URL
        return f"{StorageService.STORAGE_BASE_URL}/{subfolder}/{unique_filename}"
    
    @staticmethod
    async def save_logo(
        file_content: bytes,
        filename: str,
        user_id: uuid.UUID,
        variant: str = 'original'
    ) -> str:
        """
        Save logo file with user-specific path.
        
        Args:
            file_content: File bytes
            filename: Original filename
            user_id: User ID for organizing files
            variant: File variant (original, thumbnail, optimized, transparent)
            
        Returns:
            str: Public URL
        """
        subfolder = f"logos/{variant}/{user_id}"
        return await StorageService.save_file(file_content, filename, subfolder)
    
    @staticmethod
    async def save_preview(
        file_content: bytes,
        design_id: uuid.UUID,
        mockup_id: uuid.UUID
    ) -> str:
        """
        Save preview image.
        
        Args:
            file_content: Preview image bytes
            design_id: Customer design ID
            mockup_id: Mockup template ID
            
        Returns:
            str: Public URL
        """
        filename = f"{design_id}_{mockup_id}.jpg"
        subfolder = f"previews/{design_id}"
        return await StorageService.save_file(file_content, filename, subfolder)
    
    @staticmethod
    async def save_template_thumbnail(
        file_content: bytes,
        template_id: uuid.UUID
    ) -> str:
        """
        Save template thumbnail.
        
        Args:
            file_content: Thumbnail bytes
            template_id: Template ID
            
        Returns:
            str: Public URL
        """
        filename = f"{template_id}.png"
        subfolder = "templates/thumbnails"
        return await StorageService.save_file(file_content, filename, subfolder)
    
    @staticmethod
    async def save_mockup_image(
        file_content: bytes,
        product_id: uuid.UUID,
        view_type: str
    ) -> str:
        """
        Save mockup template image.
        
        Args:
            file_content: Mockup image bytes
            product_id: Product ID
            view_type: View type (front, back, etc.)
            
        Returns:
            str: Public URL
        """
        filename = f"{product_id}_{view_type}.jpg"
        subfolder = "mockups"
        return await StorageService.save_file(file_content, filename, subfolder)
    
    @staticmethod
    async def delete_file(url: str) -> bool:
        """
        Delete file from storage.
        
        Args:
            url: Public URL of the file
            
        Returns:
            bool: True if deleted successfully
        """
        try:
            # Extract path from URL
            path_part = url.replace(StorageService.STORAGE_BASE_URL, '')
            file_path = StorageService.STORAGE_BASE_PATH / path_part.lstrip('/')
            
            # Delete file
            if file_path.exists():
                file_path.unlink()
                return True
            
            return False
            
        except Exception as e:
            print(f"Failed to delete file {url}: {e}")
            return False
    
    @staticmethod
    def get_file_path(url: str) -> Optional[Path]:
        """
        Get local file path from public URL.
        
        Args:
            url: Public URL
            
        Returns:
            Path or None if invalid
        """
        try:
            path_part = url.replace(StorageService.STORAGE_BASE_URL, '')
            file_path = StorageService.STORAGE_BASE_PATH / path_part.lstrip('/')
            
            if file_path.exists():
                return file_path
            
            return None
            
        except Exception:
            return None
