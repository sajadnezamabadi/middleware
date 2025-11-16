from __future__ import annotations

from typing import Union

from django.http import JsonResponse
from rest_framework import status


class CustomResponse(JsonResponse):
    """
    Standard JSON response wrapper.
    {
      "data": ...,
      "message": ...,
      "error": ...,
      "error_type": ...
    }
    """

    def __init__(
        self,
        *,
        data: Union[str, dict, list, None] = None,
        message: Union[str, None] = None,
        error: Union[str, None] = None,
        error_type: Union[str, None] = None,
        status: int = status.HTTP_200_OK,
        **kwargs
    ):
        super().__init__(
            data={
                "data": data,
                "message": message,
                "error": error,
                "error_type": error_type,
            },
            status=status,
            **kwargs,
        )


