# Tx Maker

A service for making unsigned Bitcoin transactions from arbitrary inputs.
Uses public blockchain.info service for getting available inputs.

Uses Branch-and-Bound coin selection method defined in Erhart's Master's thesis [An Evaluation of Coin Selection Strategies.][1]

[1]: http://murch.one/wp-content/uploads/2016/11/erhardt2016coinselection.pdf

**Running in docker**

```
docker-compose up -d
```

**Usage**

```bash
curl -X POST \
  http://localhost:8080/payment_transactions \
  -d '{
	"source_address": "1HCuHELi5PX8mnLTSkPv27T48K4ig4CJUP",
	"outputs": {
		"1AbrhLo1S2Li9dStQsujqTgZQD9wG1VWcG": "1.11",
		"3QGenMj5hD4LBp24xow1hsagmMDjgnDpoo": "0.58",
		"18Tx44rfsnjCVjwUBaxywpDKMPc3qkgc6f": "1.11"
	},
	"fee_kb": 2000
}'
```

Will be returned a raw unsigned transaction's hex and a list of used inputs.


**Development**

```bash
pipenv install --dev
make run (or make run-testnet for running in testnet)
```

**Linters, isort and mypy**

```
make
```

**Running tests**

```
pytest
```

**Supported env variables**

- `TESTNET` - Use testnet Bitcoin network  (default=`false`)
- `PORT` - HTTP service port number (default=`8080`)
