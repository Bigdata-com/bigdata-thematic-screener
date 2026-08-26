from bigdata_thematic_screener.taxonomy import Node, get_leaf_labels, truncate_depth


def _four_level_tree() -> Node:
    return Node(
        node=1,
        label="Main Theme",
        summary="Root theme",
        children=[
            Node(
                node=2,
                label="Exposure Category",
                summary="Category",
                children=[
                    Node(
                        node=3,
                        label="Exposure Pathway",
                        summary="Pathway",
                        children=[
                            Node(node=4, label="Leaf A", summary="A"),
                            Node(node=5, label="Leaf B", summary="B"),
                        ],
                    )
                ],
            )
        ],
    )


def test_truncate_depth_none_is_noop():
    root = _four_level_tree()
    assert truncate_depth(root, None) == root


def test_truncate_depth_to_three_drops_leaf_layer():
    root = _four_level_tree()
    truncated = truncate_depth(root, 3)

    # Root -> category -> pathway, with pathway now a leaf (leaves A/B cut off)
    assert truncated.label == "Main Theme"
    category = truncated.children[0]
    assert category.label == "Exposure Category"
    pathway = category.children[0]
    assert pathway.label == "Exposure Pathway"
    assert pathway.children == []
    assert get_leaf_labels(truncated) == ["Exposure Pathway"]


def test_truncate_depth_to_two_drops_two_layers():
    root = _four_level_tree()
    truncated = truncate_depth(root, 2)
    assert truncated.children[0].children == []
    assert get_leaf_labels(truncated) == ["Exposure Category"]


def test_truncate_depth_does_not_mutate_original():
    root = _four_level_tree()
    truncate_depth(root, 2)
    assert get_leaf_labels(root) == ["Leaf A", "Leaf B"]
