"""
Test cases for vector search functionality
"""

import pytest
import tempfile
import asyncio
from pathlib import Path
from datetime import datetime

from ..modules.embeddings import EmbeddingGenerator, VectorSimilarity
from ..modules.search_engine import HybridSearchEngine, SearchConfig
from ..modules.connection_pool import get_db_connection
from ..modules.data_types import FindCommand, PocketItem, AddCommand
from ..modules.functionality.add import add


class TestEmbeddingGenerator:
    """Test the embedding generation functionality"""
    
    def test_embedding_generation(self):
        """Test basic embedding generation"""
        try:
            generator = EmbeddingGenerator()
            text = "This is a test document about machine learning and AI"
            embedding = generator.generate_embedding(text)
            
            # Check that embedding is generated
            assert embedding is not None
            assert len(embedding) == 384  # all-MiniLM-L6-v2 dimension
            assert embedding.dtype.name == 'float32'
            
            print(f"✓ Generated embedding with shape: {embedding.shape}")
        except ImportError:
            pytest.skip("sentence-transformers not available")
        except Exception as e:
            pytest.fail(f"Embedding generation failed: {e}")
    
    def test_text_preprocessing(self):
        """Test text preprocessing functionality"""
        try:
            generator = EmbeddingGenerator()
            
            # Test text cleaning
            messy_text = "  This   is    a  messy   text  with   extra   spaces  "
            clean_text = generator.preprocess_text(messy_text)
            expected = "This is a messy text with extra spaces"
            assert clean_text == expected
            
            # Test text chunking
            long_text = "A" * 1000
            chunks = generator.chunk_text(long_text, chunk_size=100, overlap=10)
            assert len(chunks) > 1
            assert all(len(chunk) <= 100 for chunk in chunks)
            
            print(f"✓ Text preprocessing works correctly")
        except ImportError:
            pytest.skip("sentence-transformers not available")
    
    def test_batch_embedding_generation(self):
        """Test batch embedding generation"""
        try:
            generator = EmbeddingGenerator()
            texts = [
                "First document about Python programming",
                "Second document about machine learning",
                "Third document about data science"
            ]
            
            embeddings = generator.generate_embeddings_batch(texts)
            
            assert len(embeddings) == len(texts)
            assert all(emb.shape == (384,) for emb in embeddings)
            
            print(f"✓ Batch embedding generation works correctly")
        except ImportError:
            pytest.skip("sentence-transformers not available")


class TestVectorSimilarity:
    """Test vector similarity calculations"""
    
    def test_cosine_similarity(self):
        """Test cosine similarity calculation"""
        import numpy as np
        
        # Test identical vectors
        v1 = np.array([1, 0, 0])
        v2 = np.array([1, 0, 0])
        similarity = VectorSimilarity.cosine_similarity(v1, v2)
        assert abs(similarity - 1.0) < 0.001
        
        # Test orthogonal vectors
        v1 = np.array([1, 0, 0])
        v2 = np.array([0, 1, 0])
        similarity = VectorSimilarity.cosine_similarity(v1, v2)
        assert abs(similarity) < 0.001
        
        print(f"✓ Cosine similarity calculation works correctly")
    
    def test_similarity_search(self):
        """Test similarity search functionality"""
        import numpy as np
        
        # Create test embeddings
        query = np.array([1, 0, 0])
        embeddings = [
            np.array([1, 0, 0]),      # Identical - should be top result
            np.array([0.9, 0.1, 0]),  # Similar - should be second
            np.array([0, 1, 0]),      # Orthogonal - should be filtered out
            np.array([0.8, 0.2, 0])   # Similar - should be third
        ]
        
        results = VectorSimilarity.similarity_search(
            query, embeddings, top_k=5, similarity_threshold=0.5
        )
        
        # Should return 3 results (excluding orthogonal vector)
        assert len(results) == 3
        
        # Results should be sorted by similarity (highest first)
        assert results[0][1] > results[1][1] > results[2][1]
        
        print(f"✓ Similarity search works correctly")


class TestHybridSearch:
    """Test the hybrid search engine"""
    
    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database for testing"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            yield Path(tmp.name)
        # Clean up
        Path(tmp.name).unlink(missing_ok=True)
    
    @pytest.fixture
    def sample_data(self, temp_db_path):
        """Add sample data to test database"""
        sample_items = [
            ("Python programming tutorial", ["python", "programming", "tutorial"]),
            ("Machine learning with Python", ["python", "ml", "data-science"]),
            ("JavaScript web development", ["javascript", "web", "frontend"]),
            ("Data analysis and visualization", ["python", "data-science", "visualization"]),
            ("React component development", ["react", "javascript", "frontend"])
        ]
        
        items = []
        for text, tags in sample_items:
            command = AddCommand(
                text=text,
                tags=tags,
                db_path=temp_db_path
            )
            item = add(command)
            items.append(item)
        
        return items
    
    def test_vector_search_integration(self, temp_db_path, sample_data):
        """Test vector search integration"""
        try:
            # Create search engine
            config = SearchConfig(
                vector_weight=1.0,  # Use only vector search for this test
                fts_weight=0.0,
                fuzzy_weight=0.0,
                enable_caching=False
            )
            search_engine = HybridSearchEngine(config)
            
            # Create search command
            command = FindCommand(
                text="Python data science",
                mode="vector",
                limit=3,
                db_path=temp_db_path
            )
            
            # Run search
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            results = loop.run_until_complete(search_engine.search(command))
            loop.close()
            
            # Should find relevant items
            assert len(results) > 0
            assert any("python" in result.item.text.lower() for result in results)
            
            print(f"✓ Vector search integration works correctly")
            
        except ImportError:
            pytest.skip("sentence-transformers not available")
        except Exception as e:
            pytest.fail(f"Vector search integration failed: {e}")
    
    def test_hybrid_search_scoring(self, temp_db_path, sample_data):
        """Test hybrid search with multiple scoring methods"""
        try:
            # Create search engine with hybrid scoring
            config = SearchConfig(
                vector_weight=0.4,
                fts_weight=0.4,
                fuzzy_weight=0.2,
                enable_caching=False,
                parallel_search=True
            )
            search_engine = HybridSearchEngine(config)
            
            # Create search command
            command = FindCommand(
                text="Python programming",
                mode="hybrid",
                limit=5,
                db_path=temp_db_path
            )
            
            # Run search
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            results = loop.run_until_complete(search_engine.search(command))
            loop.close()
            
            # Should find relevant items with combined scoring
            assert len(results) > 0
            
            # Check that scoring components are present
            for result in results:
                assert hasattr(result, 'vector_score')
                assert hasattr(result, 'fts_score')
                assert hasattr(result, 'fuzzy_score')
                assert hasattr(result, 'total_score')
                assert result.total_score > 0
            
            print(f"✓ Hybrid search scoring works correctly")
            
        except ImportError:
            pytest.skip("sentence-transformers not available")
        except Exception as e:
            pytest.fail(f"Hybrid search scoring failed: {e}")
    
    def test_search_caching(self, temp_db_path, sample_data):
        """Test search result caching"""
        try:
            # Create search engine with caching enabled
            config = SearchConfig(
                enable_caching=True,
                cache_ttl_minutes=1
            )
            search_engine = HybridSearchEngine(config)
            
            # Create search command
            command = FindCommand(
                text="Python tutorial",
                mode="hybrid",
                limit=3,
                db_path=temp_db_path
            )
            
            # Run search twice
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # First search
            results1 = loop.run_until_complete(search_engine.search(command))
            
            # Second search (should use cache)
            results2 = loop.run_until_complete(search_engine.search(command))
            
            loop.close()
            
            # Results should be identical
            assert len(results1) == len(results2)
            if results1:
                assert results1[0].item.id == results2[0].item.id
            
            print(f"✓ Search caching works correctly")
            
        except ImportError:
            pytest.skip("sentence-transformers not available")
        except Exception as e:
            pytest.fail(f"Search caching failed: {e}")


def test_database_schema_migration(tmp_path):
    """Test that database schema migration works correctly"""
    db_path = tmp_path / "test_migration.db"
    
    # Create old-style database (without embedding columns)
    import sqlite3
    db = sqlite3.connect(str(db_path))
    db.execute("""
        CREATE TABLE POCKET_PICK (
            id TEXT PRIMARY KEY,
            created TIMESTAMP NOT NULL,
            text TEXT NOT NULL,
            tags TEXT NOT NULL
        )
    """)
    db.commit()
    db.close()
    
    # Now initialize with new schema (should trigger migration)
    from ..modules.init_db import init_db
    migrated_db = init_db(db_path)
    
    # Check that new columns exist
    cursor = migrated_db.execute("PRAGMA table_info(POCKET_PICK)")
    columns = [row[1] for row in cursor.fetchall()]
    
    assert 'embedding' in columns
    assert 'embedding_model' in columns
    assert 'embedding_updated' in columns
    
    migrated_db.close()
    
    print(f"✓ Database schema migration works correctly")


if __name__ == "__main__":
    # Run basic tests if script is executed directly
    print("Running vector search tests...")
    
    try:
        # Test embedding generation
        test_gen = TestEmbeddingGenerator()
        test_gen.test_embedding_generation()
        test_gen.test_text_preprocessing()
        test_gen.test_batch_embedding_generation()
        
        # Test vector similarity
        test_sim = TestVectorSimilarity()
        test_sim.test_cosine_similarity()
        test_sim.test_similarity_search()
        
        # Test database migration
        import tempfile
        with tempfile.TemporaryDirectory() as tmp_dir:
            test_database_schema_migration(Path(tmp_dir))
        
        print("\n✅ All basic tests passed!")
        print("\nTo run full test suite with database integration:")
        print("pytest src/mcp_server_pocket_pick/tests/test_vector_search.py -v")
        
    except ImportError as e:
        print(f"⚠️  Some dependencies not available: {e}")
        print("Install missing dependencies: pip install sentence-transformers faiss-cpu")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise