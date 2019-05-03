import sys

from pydantic import BaseSettings, ValidationError


class Settings(BaseSettings):
    port: int = 8080
    testnet: bool = False

    @property
    def min_confirmations(self) -> int:
        if self.testnet and not hasattr(sys, "_called_from_test"):
            return 0
        return 6

    @property
    def blockchain_info_base_url(self) -> str:
        if self.testnet:
            return 'https://testnet.blockchain.info'
        return 'https://blockchain.info'

    @property
    def btc_network(self) -> str:
        if self.testnet:
            return 'test'
        return 'main'

    class Config:
        env_prefix = ''
        case_insensitive = True


class ConfigurationError(Exception):
    pass


try:
    settings = Settings()
except ValidationError as e:
    msg = f"Configuration error. Please specify all the env variables properly:\n\n{e}\n"
    raise ConfigurationError(msg)


if __name__ == "__main__":
    print(settings)
