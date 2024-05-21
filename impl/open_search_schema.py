from opensearchpy import OpenSearch
from opensearch_dsl import Search, Q
from django.conf import settings
import urllib

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
                "type": "text",
                "fields": {
                    "keyword": {
                        "type": "keyword",
                        "ignore_above": 256
                    }
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


parsed_url = urllib.parse.urlparse(settings.OPENSEARCH_BASE)
client = OpenSearch(
    hosts = [{'host': parsed_url.hostname, 'port': parsed_url.port}],
    http_compress = True, # enables gzip compression for request bodies
    http_auth = (settings.OPENSEARCH_USER, settings.OPENSEARCH_PASSWORD),
    use_ssl = True,
    verify_certs = True,
    ssl_assert_hostname = False,
    ssl_show_warn = False
)


def create_index():
    client.indices.create(index=settings.OPENSEARCH_INDEX, body=OPEN_SEARCH_SCHEMA)


def index_exists():
    return client.indices.exists(index=settings.OPENSEARCH_INDEX)