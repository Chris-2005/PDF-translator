from abc import ABC, abstractmethod
import yaml


class BasePDFProcessor(ABC):
    def __init__(self, config):
        self.config = config

    @abstractmethod
    def run(self):
        """子类必须实现的具体处理逻辑"""
        pass