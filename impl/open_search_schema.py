from django.conf import settings
from impl.open_search_doc import OpenSearchDoc

# This schema was originally dumped from the OpenSearch index once I had it in the right format.
# I needed to specifically add the identifier (ark/doi) as a keyword field to make it searchable.

# I believe the code to dump this was something like
# mapping = client.indices.get_mapping(index=index_name)

# if the index doesn't exist, it will use this schema to create it when running the opensearch-update django
# management command.  If it exists, it leaves it alone.

OPEN_SEARCH_SCHEMA = {
    "mappings": {
        "properties": {
            "agent_role": {
                "type": "text",
                "fields": {
                    "keyword": {
                        "type": "keyword",
                        "ignore_above": 256
                    }
                }
            },
            "create_time": {
                "type": "date"
            },
            "crossref_message": {
                "type": "text",
                "fields": {
                    "keyword": {
                        "type": "keyword",
                        "ignore_above": 256
                    }
                }
            },
            "crossref_status": {
                "type": "text",
                "fields": {
                    "keyword": {
                        "type": "keyword",
                        "ignore_above": 256
                    }
                }
            },
            "datacenter": {
                "properties": {
                    "symbol": {
                        "type": "text",
                        "fields": {
                            "keyword": {
                                "type": "keyword",
                                "ignore_above": 256
                            }
                        }
                    },
                    "name": {
                        "type": "text",
                        "fields": {
                            "keyword": {
                                "type": "keyword",
                                "ignore_above": 256
                            }
                        }
                    },
                    "id": {
                        "type": "long"
                    },
                }
            },
            "db_identifier_id": {
                "type": "long"
            },
            "exported": {
                "type": "boolean"
            },
            "has_issues": {
                "type": "boolean"
            },
            "has_metadata": {
                "type": "boolean"
            },
            "id": {
                "type": "text",
                "fields": {
                    "keyword": {
                        "type": "keyword",
                        "ignore_above": 256
                    }
                }
            },
            "identifier_type": {
                "type": "text",
                "fields": {
                    "keyword": {
                        "type": "keyword",
                        "ignore_above": 256
                    }
                }
            },
            "is_test": {
                "type": "boolean"
            },
            "link_is_broken": {
                "type": "boolean"
            },
            "oai_visible": {
                "type": "boolean"
            },
            "open_search_updated": {
                "type": "date"
            },
            "owner": {
                "properties": {
                    "account_email": {
                        "type": "text",
                        "fields": {
                            "keyword": {
                                "type": "keyword",
                                "ignore_above": 256
                            }
                        }
                    },
                    "display_name": {
                        "type": "text",
                        "fields": {
                            "keyword": {
                                "type": "keyword",
                                "ignore_above": 256
                            }
                        }
                    },
                    "id": {
                        "type": "long"
                    },
                    "username": {
                        "type": "text",
                        "fields": {
                            "keyword": {
                                "type": "keyword",
                                "ignore_above": 256
                            }
                        }
                    }
                }
            },
            "ownergroup": {
                "properties": {
                    "id": {
                        "type": "long"
                    },
                    "name": {
                        "type": "text",
                        "fields": {
                            "keyword": {
                                "type": "keyword",
                                "ignore_above": 256
                            }
                        }
                    },
                    "organization": {
                        "type": "text",
                        "fields": {
                            "keyword": {
                                "type": "keyword",
                                "ignore_above": 256
                            }
                        }
                    }
                }
            },
            "profile": {
                "properties": {
                    "id": {
                        "type": "long"
                    },
                    "label": {
                        "type": "text",
                        "fields": {
                            "keyword": {
                                "type": "keyword",
                                "ignore_above": 256
                            }
                        }
                    }
                }
            },
            "public_search_visible": {
                "type": "boolean"
            },
            "resource": {
                "properties": {
                    "creators": {
                        "type": "text",
                        "fields": {
                            "keyword": {
                                "type": "keyword",
                                "ignore_above": 256
                            }
                        }
                    },
                    "publication_date": {
                        "type": "text",
                        "fields": {
                            "keyword": {
                                "type": "keyword",
                                "ignore_above": 256
                            }
                        }
                    },
                    "publisher": {
                        "type": "text",
                        "fields": {
                            "keyword": {
                                "type": "keyword",
                                "ignore_above": 256
                            }
                        }
                    },
                    "title": {
                        "type": "text",
                        "fields": {
                            "keyword": {
                                "type": "keyword",
                                "ignore_above": 256
                            }
                        }
                    },
                    "type": {
                        "type": "text",
                        "fields": {
                            "keyword": {
                                "type": "keyword",
                                "ignore_above": 256
                            }
                        }
                    },
                    "searchable_type": {
                        "type": "text",
                        "fields": {
                            "keyword": {
                                "type": "keyword",
                                "ignore_above": 64
                            }
                        }
                    },
                    "resource_type_words": {
                        "type": "text",
                        "fields": {
                            "keyword": {
                                "type": "keyword",
                                "ignore_above": 128
                            }
                        }
                    }
                }
            },
            "searchable_id": {
                "type": "keyword"
            },
            "status": {
                "type": "text",
                "fields": {
                    "keyword": {
                        "type": "keyword",
                        "ignore_above": 256
                    }
                }
            },
            "target": {
                "type": "text",
                "fields": {
                    "keyword": {
                        "type": "keyword",
                        "ignore_above": 256
                    }
                }
            },
            "unavailable_reason": {
                "type": "text",
                "fields": {
                    "keyword": {
                        "type": "keyword",
                        "ignore_above": 256
                    }
                }
            },
            "update_time": {
                "type": "date"
            },
            "word_bucket": {
                "type": "text",
                "fields": {
                    "keyword": {
                        "type": "keyword",
                        "ignore_above": 256
                    }
                }
            }
        }
    }
}


client = OpenSearchDoc.CLIENT


def create_index(index_name=settings.OPENSEARCH_INDEX):
    body = {
        "settings": {
            "number_of_shards": 3,
            "number_of_replicas": 1
        },
        "mappings": OPEN_SEARCH_SCHEMA["mappings"]
    }
    client.indices.create(index=index_name, body=body)


def index_exists(index_name=settings.OPENSEARCH_INDEX):
    return OpenSearchDoc.index_exists(index_name=index_name)