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

from typing import Union, List, Optional

import pyrogram
from pyrogram import raw, enums
from pyrogram import types
from pyrogram import utils


class EditMessageText:
    async def edit_message_text(
        self: "pyrogram.Client",
        chat_id: Union[int, str],
        message_id: int,
        text: str,
        parse_mode: Optional["enums.ParseMode"] = None,
        entities: List["types.MessageEntity"] = None,

        # ✅ NEW PARAM (main feature)
        link_preview_options: Optional["types.LinkPreviewOptions"] = None,

        # ✅ backward compatibility (old system)
        disable_web_page_preview: bool = None,
        invert_media: bool = None,

        reply_markup: "types.InlineKeyboardMarkup" = None,
        business_connection_id: str = None
    ) -> "types.Message":

        # ✅ Backward compatibility (old → new)
        if disable_web_page_preview is not None or invert_media is not None:
            link_preview_options = types.LinkPreviewOptions(
                is_disabled=disable_web_page_preview,
                show_above_text=invert_media
            )

        # ✅ Default fallback (like Pyrogram)
        link_preview_options = link_preview_options or getattr(self, "link_preview_options", None)

        peer = await self.resolve_peer(chat_id)

        # ✅ FULL Pyrogram-style EditMessage (with media support)
        rpc = raw.functions.messages.EditMessage(
            peer=peer,
            id=message_id,

            # preview control
            no_webpage=getattr(link_preview_options, "is_disabled", None),
            invert_media=getattr(link_preview_options, "show_above_text", None),

            # ✅ IMPORTANT: this enables custom preview URL
            media=(
                raw.types.InputMediaWebPage(
                    url=link_preview_options.url,
                    force_large_media=link_preview_options.prefer_large_media,
                    force_small_media=link_preview_options.prefer_small_media,
                    optional=True
                )
                if link_preview_options and link_preview_options.url
                else None
            ),

            reply_markup=await reply_markup.write(self) if reply_markup else None,
            **await utils.parse_text_entities(self, text, parse_mode, entities)
        )

        # invoke
        if business_connection_id is not None:
            r = await self.invoke(
                raw.functions.InvokeWithBusinessConnection(
                    connection_id=business_connection_id,
                    query=rpc
                )
            )
        else:
            r = await self.invoke(rpc)

        # parse response
        for i in r.updates:
            if isinstance(i, (raw.types.UpdateEditMessage, raw.types.UpdateEditChannelMessage)):
                return await types.Message._parse(
                    self, i.message,
                    {i.id: i for i in r.users},
                    {i.id: i for i in r.chats}
                )
