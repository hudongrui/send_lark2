#!/bin/bash
export CARD_VAR='AAqd3vZhVkYrm'  # variables
export CARD_NO_VAR='AAqIiOiku9DB4'  # no vars

# python3 ../send_lark -d -i $CARD_VAR -c vars.json dongruihu

# python3 ../send_lark -d -i $CARD_NO_VAR dongruihu

python3 ../send_lark -d -i $CARD_VAR -c vars.json -r dongruihu
