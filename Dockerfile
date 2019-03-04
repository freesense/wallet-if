FROM wallet-base:0.0.3
COPY *.py /app/
WORKDIR /app
CMD ./wallet.py wbitcoin wusdt wethereum wlitecoin
EXPOSE 25565
