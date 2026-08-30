arrs=(ptr_chase  stream-add  stream-copy  stream-scale  stream-triad  )
bins=(../../../../benchmarks/ptr_chase/ptr_chase  ../../../../benchmarks/stream-add/testing/stream_omp  ../../../../benchmarks/stream-copy/testing/stream_omp  ../../../../benchmarks/stream-scale/testing/stream_omp  ../../../../benchmarks/stream-triad/testing/stream_omp  )



for ((i=0; i<${#arrs[@]}; i++))
do
        arra=${arrs[$i]}
        bin=${bins[$i]}


        
        export arr=$arra

        # creat simulation folder
        echo "============================================================="
        echo "Benchmark: ${arr}"
        echo "============================================================="
        if [ -d "${arr}" ]; then
                rm -rf "${arr}"
        fi
        mkdir -p "${arr}"
        cd "${arr}"



        # add the config file,  binaries, and input data to the simulation folder 
        cp ../sb.cfg ./
        cp "$bin" ./binary
        cp ../run-one.sh ./
        

        if [ "$arra" = "ptr_chase" ]; then

                cp ../../../../benchmarks/ptr_chase/array.dat ./
                cp ../sb_ptr.cfg ./sb.cfg
        fi


        ./run-one.sh
        
        
        # put the command to run the simulation
        


        
        cd ../
done
