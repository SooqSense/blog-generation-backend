from typing import Optional, Dict, Any, List

from .base_client import APIClient


class ImageAPI:
    """API client for image generation endpoints"""

    def __init__(self):
        self.client = APIClient()

    def generate_image(self, **kwargs) -> Optional[Dict[str, Any]]:
        return self.client.post("image-generation/generate-image/", data=kwargs)

    def edit_image(self, **kwargs) -> Optional[Dict[str, Any]]:
        return self.client.post("image-generation/edit-image/", data=kwargs)

    def list_images(self) -> Optional[Dict[str, Any]]:
        return self.client.get("image-generation/images/")

    def delete_images(self, ids: List[int]) -> Optional[Dict[str, Any]]:
        return self.client.delete("image-generation/delete/", data={'ids': ids})

    def get_image(self, image_id: int) -> Optional[Dict[str, Any]]:
        response = self.client.get("image-generation/images/")
        if response and 'data' in response:
            for image in response['data']:
                if image.get('id') == image_id:
                    return {'success': True, 'data': image}
        return None

    def get(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        return self.client.get(endpoint, params=params)


