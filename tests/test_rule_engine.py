import pytest
from app.rule_engine import apply_rules, evaluate_rule

def test_basic_rule_match():
    payload = {"Product": "Chocolate", "Price": 1.8}
    conditions = [(1, "=", "Product", "Chocolate"), (1, "<", "Price", 2)]
    assert evaluate_rule(payload, conditions) is True

def test_rule_no_match():
    payload = {"Product": "Chocolate", "Price": 2.2}
    conditions = [(1, "=", "Product", "Chocolate"), (1, "<", "Price", 2)]
    assert evaluate_rule(payload, conditions) is False

def test_or_groups():
    payload = {"CompanyName": "Google", "Price": 10}
    conds = [
        (1, "=", "CompanyName", "Google"),  # group 1 -> true
        (2, "=", "CompanyName", "Amazon"),
        (2, "<", "Price", 2.5),
    ]
    assert evaluate_rule(payload, conds) is True

def test_apply_all_matching_rules_priority_sort():
    payload = {"Product": "Chocolate", "Price": 3}
    rules = [
        {"id":1,"label":"Green","priority":10,"conditions":[(1,"=", "Product","Chocolate"), (1,"<", "Price",2)]},
        {"id":2,"label":"Yellow","priority":20,"conditions":[(1,"=", "Product","Chocolate"), (1,">=", "Price",2), (1,"<","Price",5)]},
        {"id":3,"label":"Red","priority":30,"conditions":[(1,"=", "Product","Chocolate"), (1,">=","Price",5)]}
    ]
    labels, ids = apply_rules(payload, rules)
    assert labels == ["Yellow"]
    assert ids == [2]
