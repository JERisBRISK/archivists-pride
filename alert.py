import dearpygui.dearpygui as dpg

# inspired by https://discord.com/channels/736279277242417272/876200434468016178/879776888824922122

def alert(title, message):

    # guarantee these commands happen in the same frame
    with dpg.mutex():

        viewport_width = dpg.get_viewport_client_width()
        viewport_height = dpg.get_viewport_client_height()

        with dpg.window(label=title, modal=True, no_close=True) as modal_id:
            dpg.add_text(message)
            dpg.add_button(label="Ok", width=75, user_data=modal_id, callback=on_alert_confirmation)

    # guarantee these commands happen in another frame
    dpg.split_frame()
    width = dpg.get_item_width(modal_id)
    height = dpg.get_item_height(modal_id)
    dpg.set_item_pos(modal_id, [viewport_width // 2 - width // 2, viewport_height // 2 - height // 2])

def on_alert_confirmation(sender, unused, user_data):
    dpg.delete_item(user_data)


