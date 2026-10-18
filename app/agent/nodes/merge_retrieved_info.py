"""召回结果合并节点。"""

from dataclasses import replace

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import (
    ColumnInfoState,
    DataAgentState,
    MetricInfoState,
    TableInfoState,
)
from app.core.log import logger
from app.entities.column_info import ColumnInfo
from app.entities.metric_info import MetricInfo
from app.entities.table_info import TableInfo
from app.entities.value_info import ValueInfo


async def merge_retrieved_info(
    state: DataAgentState,
    runtime: Runtime[DataAgentContext],
) -> dict[str, list[TableInfoState] | list[MetricInfoState]]:
    """合并三路召回结果，生成按表组织的候选上下文。"""

    writer = runtime.stream_writer
    writer("合并召回信息")

    retrieved_column_infos: list[ColumnInfo] = state["retrieved_column_infos"]
    retrieved_metric_infos: list[MetricInfo] = state["retrieved_metric_infos"]
    retrieved_value_infos: list[ValueInfo] = state["retrieved_value_infos"]

    meta_mysql_repository = runtime.context["meta_mysql_repository"]

    # 字段 ID 是字段的唯一标识。
    # 转成字典后既能自然去重，也方便后续判断字段是否已经存在。
    column_info_map: dict[str, ColumnInfo] = {
        column_info.id: replace(
            column_info,
            examples=list(column_info.examples),
        )
        for column_info in retrieved_column_infos
    }

    # 指标召回只告诉系统“需要哪个指标”，生成 SQL 还需要指标依赖的字段。
    # 如果依赖字段没有被字段召回命中，就从 Meta MySQL 补齐。
    for metric_info in retrieved_metric_infos:
        for column_id in metric_info.relevant_columns:
            if column_id in column_info_map:
                continue

            column_info = await meta_mysql_repository.get_column_info_by_id(
                column_id,
            )

            if column_info is None:
                raise LookupError(
                    f"指标 {metric_info.id} 引用了不存在的字段: {column_id}"
                )

            column_info_map[column_id] = column_info

    # 字段值召回得到的是“真实值 + 所属字段 ID”。
    # 先保证所属字段存在，再把真实值加入字段 examples，
    # 帮助后续模型生成正确的 WHERE 条件。
    for value_info in retrieved_value_infos:
        column_id = value_info.column_id

        if column_id not in column_info_map:
            column_info = await meta_mysql_repository.get_column_info_by_id(
                column_id,
            )

            if column_info is None:
                raise LookupError(
                    f"字段值 {value_info.id} 引用了不存在的字段: {column_id}"
                )

            column_info_map[column_id] = column_info

        column_examples = column_info_map[column_id].examples

        if value_info.value not in column_examples:
            column_examples.append(value_info.value)

    # SQL 上下文需要按照“表 -> 字段列表”组织，
    # 因此把字段从按 ID 索引转换成按 table_id 分组。
    table_to_columns: dict[str, list[ColumnInfo]] = {}

    for column_info in column_info_map.values():
        table_to_columns.setdefault(
            column_info.table_id,
            [],
        ).append(column_info)

    # 主外键通常不会直接出现在用户问题中，向量召回可能遗漏。
    # 它们又是生成多表 JOIN 条件的必要信息，因此为每张候选表补齐。
    for table_id, column_infos in table_to_columns.items():
        key_columns = await meta_mysql_repository.get_key_columns_by_table_id(
            table_id,
        )
        existing_column_ids = {column_info.id for column_info in column_infos}

        for key_column in key_columns:
            if key_column.id not in existing_column_ids:
                column_infos.append(key_column)
                existing_column_ids.add(key_column.id)

    # 把完整业务实体转换成面向过滤节点和提示词的嵌套结构。
    table_infos: list[TableInfoState] = []

    for table_id, column_infos in table_to_columns.items():
        table_info: TableInfo | None = await meta_mysql_repository.get_table_info_by_id(
            table_id,
        )

        if table_info is None:
            raise LookupError(f"字段引用了不存在的表: {table_id}")

        columns = [
            ColumnInfoState(
                name=column_info.name,
                type=column_info.type,
                role=column_info.role,
                examples=column_info.examples,
                description=column_info.description,
                alias=column_info.alias,
            )
            for column_info in column_infos
        ]

        table_infos.append(
            TableInfoState(
                name=table_info.name,
                role=table_info.role,
                description=table_info.description,
                columns=columns,
            )
        )

    # 指标不需要按表分组，只需去掉内部 id，
    # 保留后续模型理解业务口径需要的信息。
    metric_infos = [
        MetricInfoState(
            name=metric_info.name,
            description=metric_info.description,
            relevant_columns=metric_info.relevant_columns,
            alias=metric_info.alias,
        )
        for metric_info in retrieved_metric_infos
    ]

    logger.info(f"合并后的表信息: {[table_info['name'] for table_info in table_infos]}")
    logger.info(
        f"合并后的指标信息: {[metric_info['name'] for metric_info in metric_infos]}"
    )

    return {
        "table_infos": table_infos,
        "metric_infos": metric_infos,
    }
