"""问数接口请求体模型功能检查。"""

from pydantic import ValidationError

from app.api.schemas.query_schema import QuerySchema


def main() -> None:
    """检查合法和非法查询请求体。"""

    payload = {
        "query": "华东地区 iPhone 的销售总额是多少？",
    }

    request = QuerySchema.model_validate(payload)

    if request.query != payload["query"]:
        raise AssertionError(f"query 解析结果不正确: {request.query}")

    if request.model_dump() != payload:
        raise AssertionError(f"请求体序列化结果不正确: {request.model_dump()}")

    invalid_payloads = [
        {},
        {
            "query": 123,
        },
    ]

    for invalid_payload in invalid_payloads:
        try:
            QuerySchema.model_validate(invalid_payload)
        except ValidationError:
            continue

        raise AssertionError(f"非法请求体没有被拒绝: {invalid_payload}")

    print("合法请求体:", request.model_dump())
    print("缺少 query 的请求体已被拒绝")
    print("query 类型错误的请求体已被拒绝")
    print("QuerySchema 功能检查通过")


if __name__ == "__main__":
    main()
