const { Pool } = require('pg');

const pool = new Pool({
    user: 'postgres',
    host: 'localhost',
    database: 'UI',
    password: '$Hulk5628',
    port: 5432,
});

async function testDB() {
    try {
        console.log("🔄 Connecting to PostgreSQL...");
        // 1. Test Connection
        const client = await pool.connect();
        console.log("✅ Successfully connected to the database!");

        console.log("\n📥 Fetching data from 'player_profiles' table...\n");
        
        // 2. Query all profiles, sorting by the most recently updated first
        const res = await client.query('SELECT * FROM player_profiles ORDER BY last_updated DESC');

        if (res.rows.length === 0) {
            console.log("⚠️ The 'player_profiles' table exists but is currently empty.");
        } else {
            console.log(`📊 Found ${res.rows.length} profile(s):\n`);
            
            // 3. Output the data nicely formatted
            res.rows.forEach((row, index) => {
                console.log(`================ PROFILE ${index + 1} ================`);
                console.log(`👤 Profile Name: ${row.profile_name}`);
                console.log(`🕒 Last Updated: ${row.last_updated}`);
                
                // mapping_data is stored as JSONB, so pg parses it as a JS object/array automatically
                const regions = Array.isArray(row.mapping_data) ? row.mapping_data : [];
                console.log(`🗺️  Regions Count: ${regions.length}`);
                
                console.log(`\n📄 Raw JSON Data:`);
                console.log(JSON.stringify(row.mapping_data, null, 2));
                console.log("==============================================\n");
            });
        }
        
        // Release the client connection
        client.release();
    } catch (err) {
        console.error("❌ Database Error:\n", err.message);
    } finally {
        // Close the pool so the script can exit
        await pool.end();
    }
}

testDB();