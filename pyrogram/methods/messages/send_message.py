#  Pyrofork - Telegram MTProto API Client Library for Python
#  Copyright (C) 2017-present Dan <https://github.com/delivrance>
#  Copyright (C) 2022-present Mayuri-Chan <https://github.com/Mayuri-Chan>
#
#  This file is part of Pyrofork.
#
#  Pyrofork is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Lesser General Public License as published
#  by the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Pyrofork is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public License
#  along with Pyrofork.  If not, see <http://www.gnu.org/licenses/>.

from datetime import datetime
from typing import Union, List, Optional

import pyrogram
from pyrogram import raw, utils, enums
from pyrogram import types


class SendMessage:
    async def send_message(
        self: "pyrogram.Client",
        chat_id: Union[int, str],
        text: str,
        parse_mode: Optional["enums.ParseMode"] = None,
        entities: List["types.MessageEntity"] = None,

        # ✅ NEW (added)
        link_preview_options: Optional["types.LinkPreviewOptions"] = None,

        # ✅ kept for backward compatibility
        disable_web_page_preview: bool = None,

        disable_notification: bool = None,
        message_thread_id: int = None,
        business_connection_id: str = None,
        reply_to_message_id: int = None,
        reply_to_story_id: int = None,
        reply_to_chat_id: int = None,
        reply_to_monoforum_id: Union[int, str] = None,
        quote_text: str = None,
        quote_entities: List["types.MessageEntity"] = None,
        schedule_date: datetime = None,
        protect_content: bool = None,
        allow_paid_broadcast: bool = None,
        invert_media: bool = None,
        message_effect_id: int = None,
        reply_markup: Union[
            "types.InlineKeyboardMarkup",
            "types.ReplyKeyboardMarkup",
            "types.ReplyKeyboardRemove",
            "types.ForceReply"
        ] = None
    ) -> "types.Message":

        # ✅ Backward compatibility (old param → new system)
        if disable_web_page_preview is not None:
            link_preview_options = types.LinkPreviewOptions(
                is_disabled=disable_web_page_preview
            )

        # ✅ Optional fallback (like Pyrogram)
        link_preview_options = link_preview_options or getattr(self, "link_preview_options", None)

        # Parse message
        message, entities = (await utils.parse_text_entities(self, text, parse_mode, entities)).values()

        # Reply handling
        reply_to = await utils.get_reply_to(
            client=self,
            chat_id=chat_id,
            reply_to_message_id=reply_to_message_id,
            reply_to_story_id=reply_to_story_id,
            message_thread_id=message_thread_id,
            reply_to_chat_id=reply_to_chat_id,
            reply_to_monoforum_id=reply_to_monoforum_id,
            quote_text=quote_text,
            quote_entities=quote_entities,
            parse_mode=parse_mode
        )

        peer = await self.resolve_peer(chat_id)

        # ✅ NEW CORE LOGIC (ported from Pyrogram)
        if link_preview_options and link_preview_options.url:
            rpc = raw.functions.messages.SendMedia(
                peer=peer,
                media=raw.types.InputMediaWebPage(
                    url=link_preview_options.url,
                    force_large_media=link_preview_options.prefer_large_media,
                    force_small_media=link_preview_options.prefer_small_media,
                    optional=True
                ),
                silent=disable_notification or None,
                invert_media=link_preview_options.show_above_text,
                reply_to=reply_to,
                random_id=self.rnd_id(),
                schedule_date=utils.datetime_to_timestamp(schedule_date),
                reply_markup=await reply_markup.write(self) if reply_markup else None,
                message=message,
                entities=entities,
                noforwards=protect_content,
                allow_paid_floodskip=allow_paid_broadcast,
                effect=message_effect_id,
            )
        else:
            rpc = raw.functions.messages.SendMessage(
                peer=peer,
                no_webpage=getattr(link_preview_options, "is_disabled", None) or None,
                silent=disable_notification or None,
                reply_to=reply_to,
                random_id=self.rnd_id(),
                schedule_date=utils.datetime_to_timestamp(schedule_date),
                reply_markup=await reply_markup.write(self) if reply_markup else None,
                message=message,
                entities=entities,
                noforwards=protect_content,
                allow_paid_floodskip=allow_paid_broadcast,
                invert_media=getattr(link_preview_options, "show_above_text", None),
                effect=message_effect_id,
            )

        # Invoke
        if business_connection_id is not None:
            r = await self.invoke(
                raw.functions.InvokeWithBusinessConnection(
                    connection_id=business_connection_id,
                    query=rpc
                )
            )
        else:
            r = await self.invoke(rpc)

        # Handle response
        if isinstance(r, raw.types.UpdateShortSentMessage):
            peer = await self.resolve_peer(chat_id)

            peer_id = (
                peer.user_id
                if isinstance(peer, raw.types.InputPeerUser)
                else -peer.chat_id
            )

            return types.Message(
                id=r.id,
                chat=types.Chat(
                    id=peer_id,
                    type=enums.ChatType.PRIVATE,
                    client=self
                ),
                text=message,
                date=utils.timestamp_to_datetime(r.date),
                outgoing=r.out,
                reply_markup=reply_markup,
                entities=[
                    types.MessageEntity._parse(None, entity, {})
                    for entity in entities
                ] if entities else None,
                client=self
            )

        for i in r.updates:
            if isinstance(i, (
                raw.types.UpdateNewMessage,
                raw.types.UpdateNewChannelMessage,
                raw.types.UpdateNewScheduledMessage,
                raw.types.UpdateBotNewBusinessMessage
            )):
                return await types.Message._parse(
                    self, i.message,
                    {i.id: i for i in r.users},
                    {i.id: i for i in r.chats},
                    is_scheduled=isinstance(i, raw.types.UpdateNewScheduledMessage),
                    business_connection_id=business_connection_id
                )
