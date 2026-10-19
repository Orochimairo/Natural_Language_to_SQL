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
) -> dict[
    str,
    list[TableInfoState] | list[MetricInfoState],
]:
    """合并三路召回结果，生成按表组织的候选上下文。"""

    step = "合并召回信息"
    writer = runtime.stream_writer

    writer(
        {
            "type": "progress",
            "step": step,
            "status": "running",
        }
    )

    try:
        retrieved_column_infos: list[ColumnInfo] = state["retrieved_column_infos"]
        retrieved_metric_infos: list[MetricInfo] = state["retrieved_metric_infos"]
        retrieved_value_infos: list[ValueInfo] = state["retrieved_value_infos"]

        meta_mysql_repository = runtime.context["meta_mysql_repository"]

        # 字段 ID 是字段的唯一标识。
        # 转成字典后既能自然去重，也方便判断字段是否存在。
        column_info_map: dict[str, ColumnInfo] = {
            column_info.id: replace(
                column_info,
                examples=list(column_info.examples),
            )
            for column_info in retrieved_column_infos
        }

        # 指标召回只告诉系统需要哪个指标。
        # 生成 SQL 还需要指标依赖的字段。
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

        # 字段值召回得到真实值及其所属字段。
        # 保证字段存在，再把真实值加入 examples。
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

        # 将字段按照所属表进行分组。
        table_to_columns: dict[
            str,
            list[ColumnInfo],
        ] = {}

        for column_info in column_info_map.values():
            table_to_columns.setdefault(
                column_info.table_id,
                [],
            ).append(column_info)

        # 补齐生成 JOIN 条件需要的主键和外键。
        for (
            table_id,
            column_infos,
        ) in table_to_columns.items():
            key_columns = await meta_mysql_repository.get_key_columns_by_table_id(
                table_id,
            )
            existing_column_ids = {column_info.id for column_info in column_infos}

            for key_column in key_columns:
                if key_column.id not in existing_column_ids:
                    column_infos.append(key_column)
                    existing_column_ids.add(key_column.id)

        # 转换为过滤节点和提示词使用的嵌套结构。
        table_infos: list[TableInfoState] = []

        for (
            table_id,
            column_infos,
        ) in table_to_columns.items():
            table_info: (
                TableInfo | None
            ) = await meta_mysql_repository.get_table_info_by_id(
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
                    description=(column_info.description),
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

        metric_infos = [
            MetricInfoState(
                name=metric_info.name,
                description=metric_info.description,
                relevant_columns=(metric_info.relevant_columns),
                alias=metric_info.alias,
            )
            for metric_info in retrieved_metric_infos
        ]

        logger.info(
            f"合并后的表信息: {[table_info['name'] for table_info in table_infos]}"
        )
        logger.info(
            f"合并后的指标信息: {[metric_info['name'] for metric_info in metric_infos]}"
        )

        writer(
            {
                "type": "progress",
                "step": step,
                "status": "success",
            }
        )

        return {
            "table_infos": table_infos,
            "metric_infos": metric_infos,
        }
    except Exception as error:
        logger.error(f"{step}失败: {error}")

        writer(
            {
                "type": "progress",
                "step": step,
                "status": "error",
            }
        )

        raise
