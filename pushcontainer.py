from contextlib import contextmanager
import dearpygui.dearpygui as dpg

@contextmanager
def push_container(id):
    try:
        dpg.push_container_stack(id)
        yield id
    finally:
        dpg.pop_container_stack()