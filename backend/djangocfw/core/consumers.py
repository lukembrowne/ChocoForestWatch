from channels.generic.websocket import AsyncJsonWebsocketConsumer

class ProgressConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        """Handle WebSocket connection"""
        # Get project_id from URL route
        self.project_id = self.scope['url_route']['kwargs']['project_id']
        self.group_name = f"project_{self.project_id}"

        # Join project group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        # Leave project group
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def training_update(self, event):
        """Handle training progress updates"""
        # Send message to WebSocket
        await self.send_json({
            'type': 'training_update',
            'progress': event['progress'],
            'message': event['message']
        })

    async def prediction_update(self, event):
        """Handle prediction progress updates"""
        # Send message to WebSocket
        await self.send_json({
            'type': 'prediction_update',
            'progress': event['progress'],
            'message': event['message']
        }) 